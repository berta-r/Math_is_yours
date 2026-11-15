"""Offline setup boundaries, payload integrity and USB volume compatibility."""
import hashlib
import json
import shutil
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from laptop.tutor_setup import checked_manifest, install, startup_command
from laptop.setup_drive import build_image
from board.usb_setup_drive import verify_image, unit_text
from board import usb_setup_drive as usb_drive


class SetupTests(unittest.TestCase):
    def payload(self, folder, extra=None):
        data={'MathTutor.exe':b'fixture program','adb/adb.exe':b'fixture adb',
              'adb/AdbWinApi.dll':b'a','adb/AdbWinUsbApi.dll':b'b'}
        data.update(extra or {})
        payload=folder/'payload.zip'
        with zipfile.ZipFile(payload,'w') as archive:
            for name,content in data.items():archive.writestr(name,content)
        manifest={'version':'1.0-test','board':{'serial':'fixture-board','port':7040},
                  'files':{name:hashlib.sha256(content).hexdigest() for name,content in data.items()}}
        return payload,manifest

    def test_tampered_payload_is_rejected_before_any_install(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload,manifest=self.payload(root)
            manifest['files']['MathTutor.exe']='0'*64
            with self.assertRaises(ValueError):install(payload,manifest,root/'install',startup=False,launch=False)
            self.assertFalse((root/'install').exists())

    def test_archive_cannot_escape_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            for bad in ('../outside.exe','C:/outside.exe','/outside.exe','dir\\outside.exe'):
                payload,manifest=self.payload(Path(folder),{bad:b'unsafe'})
                with self.assertRaises(ValueError):checked_manifest(payload,manifest)

    def test_install_is_complete_and_repeatable_without_external_python(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload,manifest=self.payload(root)
            with patch('laptop.tutor_setup.single_instance',return_value=None):
                result=install(payload,manifest,root/'Local App Data/Tutor',startup=False,launch=False)
                repeated=install(payload,manifest,root/'Local App Data/Tutor',startup=False,launch=False)
            self.assertEqual(result,repeated)
            config=json.loads((Path(result['folder'])/'config.json').read_text())
            self.assertTrue(Path(config['adb']).is_file())
            command=startup_command(Path(result['executable']),Path(result['folder'])/'config.json')
            self.assertIn('MathTutor.exe" --watch --config "',command)
            self.assertNotIn('python',command.lower())

    def test_changed_installed_version_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload,manifest=self.payload(root)
            with patch('laptop.tutor_setup.single_instance',return_value=None):
                result=install(payload,manifest,root/'installed',startup=False,launch=False)
            exe=Path(result['executable']);exe.write_bytes(b'changed')
            with self.assertRaises(ValueError):install(payload,manifest,root/'installed',startup=False,launch=False)
            self.assertEqual(exe.read_bytes(),b'changed')

    def test_held_watcher_lock_does_not_overwrite_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload,manifest=self.payload(root)
            target=root/'installed';target.mkdir()
            config=target/'config.json';config.write_text('{"port":7040,"previous":true}')
            before=config.read_bytes()
            with patch('laptop.tutor_setup.single_instance',side_effect=ValueError('busy')), patch('laptop.tutor_setup.time.monotonic',side_effect=[0,21]):
                with self.assertRaises(ValueError):install(payload,manifest,target,startup=False,launch=False)
            self.assertEqual(config.read_bytes(),before)


class VolumeTests(unittest.TestCase):
    def test_volume_chains_preserve_exact_setup_bytes_and_end_markers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'setup';content=bytes(range(256))*59;source.write_bytes(content)
            image=root/'setup.img';build_image({'START.EXE':source},image,size_mb=32)
            verify_image(image)
            with image.open('rb') as f:
                boot=f.read(512);self.assertEqual(boot[510:],b'\x55\xaa')
                sector=struct.unpack_from('<H',boot,11)[0];cluster=boot[13]
                fatsize=struct.unpack_from('<H',boot,22)[0]
                fat=f.read(fatsize*sector)
                f.seek((1+2*fatsize)*sector)
                directory=f.read(32*sector)
                self.assertEqual(directory[32:43],b'START   EXE')
                first=struct.unpack_from('<H',directory,32+26)[0]
                size=struct.unpack_from('<I',directory,32+28)[0]
                output=b'';visited=set()
                while first<0xfff8:
                    self.assertNotIn(first,visited);visited.add(first)
                    f.seek((1+2*fatsize+32+(first-2)*cluster)*sector)
                    output+=f.read(cluster*sector)
                    first=struct.unpack_from('<H',fat,first*2)[0]
                self.assertEqual(output[:size],content)
                self.assertEqual(len(visited),4)

    def test_volume_rejects_unsafe_or_duplicate_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'s';source.write_bytes(b'1')
            for files in ({'../EXE':source},{'start.exe':source,'START.EXE':source}):
                with self.assertRaises(ValueError):build_image(files,root/'image')

    def test_usb_service_adds_only_a_dependent_service(self):
        unit=unit_text()
        self.assertIn('After=adbd.service',unit)
        self.assertIn('WantedBy=adbd.service',unit)
        self.assertNotIn('restart adbd',unit)
        self.assertNotIn('math-llm',unit)


class GadgetRollbackTests(unittest.TestCase):
    def test_failed_bind_restores_existing_adb_serial_and_descriptors(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);gadget=root/'g1'
            for d in ('configs/c.1','functions/ffs.adb','functions/acm.GS0','os_desc'):
                (gadget/d).mkdir(parents=True,exist_ok=True)
            for name,value in {'idVendor':'0x2341','idProduct':'0x0078','UDC':'controller',
                    'bcdDevice':'0x0700','os_desc/use':'0','os_desc/b_vendor_code':'0x00','os_desc/qw_sign':''}.items():
                (gadget/name).write_text(value+'\n')
            try:
                for name in ('ffs.adb','acm.GS0'):(gadget/'configs/c.1'/name).symlink_to(gadget/'functions'/name,target_is_directory=True)
            except OSError:
                self.skipTest('Creating test symlinks requires developer mode or privilege on Windows')
            source=root/'source';source.write_bytes(b'fixture')
            image=root/'drive.img';build_image({'START.EXE':source},image,size_mb=32)
            real_mkdir=Path.mkdir;real_rmdir=Path.rmdir;real_write=usb_drive.write
            def mkdir(path,*args,**kwargs):
                result=real_mkdir(path,*args,**kwargs)
                if path.name==usb_drive.FUNCTION:
                    real_mkdir(path/'lun.0')
                    for name in ('ro','removable','cdrom','file'):(path/'lun.0'/name).touch()
                return result
            def rmdir(path):
                if path.name==usb_drive.FUNCTION:
                    for p in (path/'lun.0').iterdir():p.unlink()
                    real_rmdir(path/'lun.0')
                return real_rmdir(path)
            failed=False
            def write(path,value):
                nonlocal failed
                if Path(path)==gadget/'UDC' and value=='controller' and not failed:
                    failed=True
                    raise OSError('Injected USB bind failure')
                return real_write(path,value)
            with patch.object(Path,'mkdir',mkdir),patch.object(Path,'rmdir',rmdir),patch.object(usb_drive,'write',write),patch.object(usb_drive.subprocess,'run'):
                with self.assertRaises(OSError):usb_drive.attach(gadget,image,root/'saved.json')
            self.assertEqual((gadget/'UDC').read_text().strip(),'controller')
            self.assertEqual((gadget/'bcdDevice').read_text().strip(),'0x0700')
            self.assertEqual((gadget/'os_desc/use').read_text().strip(),'0')
            self.assertFalse((gadget/'configs/c.1'/usb_drive.FUNCTION).exists())
            self.assertTrue((gadget/'configs/c.1/ffs.adb').is_symlink())
            self.assertTrue((gadget/'configs/c.1/acm.GS0').is_symlink())


if __name__=='__main__':unittest.main()
