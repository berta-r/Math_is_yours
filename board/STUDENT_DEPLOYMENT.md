# Student tutor deployment (Wi-Fi setup, USB use)

The UNO Q Linux side runs the application, local SLM and SQLite records. The PC
renders the page and carries HTTP over USB. All model/data preparation happens
before use; the student session needs no Wi-Fi or internet.

The application, local-model hints, images and learning graph have been tested on
the physical UNO Q over Wi-Fi and USB. A subsequent board boot started the tutor
and both models automatically and retained the test notebook. The standalone
Windows launcher is now installed on the development PC. Its login command has
been tested, but an actual Windows reboot/login and a fresh PC remain unverified.
The setup-drive service is active/enabled. Windows mounted **MATHTUTOR (D:)**,
verified its installer, and selected inbox drivers for storage, WinUSB and serial.
The installed watcher reopened the tutor automatically after USB reconfiguration
and a full shutdown/replug. The drive returned, all four services started, the
model became ready and saved progress remained intact. Windows confirms that the
setup volume is read-only; the user confirmed both drive and browser appeared.
The Windows launcher needs a one-time installation on each PC. A USB device alone
cannot reliably open a browser on an arbitrary, unprepared computer.

## Wi-Fi connection for setup and testing

The PC and UNO Q must be on the same network. Use the address shown in App Lab,
or run `hostname -I` in its board terminal. SSH access is separate from the App Lab
session. An SSH public key can be added to the `arduino` user's `authorized_keys`;
keep the private key on the PC and type passwords only into a local terminal.

The same deployment archive below can be uploaded with SCP to a new directory
under `/home/arduino/math-tutor-releases/`. Verify its SHA-256 before extracting,
then run the existing service installer from that release. Check for running
evaluations first, preserve earlier release folders, and do not switch or modify
the team's board Git checkout. The installer requires sudo authentication for the
boot service. Successful SSH key login does not grant password-free sudo.

The app continues to listen on board loopback. On the **PC**, forward its port
(substitute the board address and, if needed, add `-i PATH_TO_PRIVATE_KEY`):

```powershell
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -N -L 127.0.0.1:7012:127.0.0.1:7011 arduino@BOARD_IP
```

Keep that command running, then open **http://127.0.0.1:7012** on the PC. Port 7012
leaves the laptop prototype on 7011 available. No router port forwarding or public
web hosting is needed. When the tunnel stops, reopen it to reconnect. SSH carries
the browser traffic over the local Wi-Fi; models and student records stay on the
board. The later USB forward carries the same application traffic without Wi-Fi.

For preparation only, the embedding service can also be forwarded to local port
18082 (`-L 127.0.0.1:18082:127.0.0.1:8082`). On the **PC**, run
`python laptop/build_skill_graph.py --features embeddings --port 18082 --threshold 0.65`
before building the archive. This exports related skill pairs from authored
descriptions; it does not modify prerequisite edges or student estimates.

## Prepare the board once

Complete [guide steps 0–7](../docs/DATATHON-GUIDE.md) for the UNO Q 4 GB, including pinned
models and `math-llm.service`. Use the existing model installation; the tutor does
not start another inference server or load embeddings into its own process.
The application service is separate from App Lab and uses standard-library Python.
The LED matrix adapter remains separate work; no external button is needed.

On the **Windows PC**, Python 3 and ADB must be available. Arduino App Lab's bundled
ADB and Android platform-tools are detected automatically. A custom executable can
be supplied with `--adb`. First find the board's exact USB serial:

```powershell
python laptop/usb_launcher.py devices
```

Connect using a data-capable cable and adequate board power. If no serial appears,
complete the board/USB setup first. Multiple connected devices are safe: every
subsequent command explicitly selects the configured serial.

Build a reviewable deployment archive on the **PC** before any board changes:

```powershell
python laptop/deploy_student.py --with-data
```

The archive is in ignored `results/math-tutor-bundle.tar.gz`. It contains runtime
code, assets, the curriculum, optional prepared training data/images/annotations,
and any precomputed `data/skill_graph.json`. It excludes validation data, model
weights, virtual environments, credentials and progress databases. Omit
`--with-data` for the original diagnostic/sample demo.

Upload and install from the **PC** (replace `BOARD_SERIAL`):

```powershell
python laptop/deploy_student.py --serial BOARD_SERIAL --with-data --install --local-tutor
```

This checks that the USB device identifies itself as UNO Q, creates a new release
directory in its home folder, transfers the archive, verifies its SHA-256, and
runs the service installer. If sudo asks for the board password, type it yourself
in the terminal. Passwords are never stored. Do not deploy over a teammate's
ongoing board evaluation.

`--local-tutor` requires the existing `math-llm.service`; omit it for stored hints.
To inspect/install an already copied release, run **on the board** from its folder:

```bash
python3 board/install_student_service.py --local-tutor --print-unit
python3 board/install_student_service.py --local-tutor
systemctl status math-student math-llm --no-pager
curl http://127.0.0.1:7011/api/health
free -m
```

The service runs as the unprivileged `arduino` user, starts on boot, restarts on
failure and writes progress to `/var/lib/math-student/progress.db`. New code
releases reuse that location. The application has a 256 MB systemd memory limit;
the model has its own service and memory use. Measure the whole board under load
before claiming RAM/latency compliance.

To migrate an earlier profile database, copy a consistent SQLite snapshot to the
board and pass `--import-progress /path/to/snapshot.db` to the installer. This is
accepted only when the board's persistent database does not already exist; it
never overwrites existing student records. The PC prototype database is not
automatically uploaded. Use Python's SQLite backup API to snapshot a database
that might be in use.

## Install automatic opening on the Windows PC

### Test without installing additional software

On a PC that **already has Python and ADB**, the repository's watcher can run
temporarily. It does not copy an installed launcher or register Windows startup:

```powershell
python laptop/usb_launcher.py devices
python laptop/usb_launcher.py watch --serial BOARD_SERIAL --port 7013
```

Keep that process running during the test. It waits for the specified board,
opens its browser page when the app is ready, and watches for reconnection. Stop
it with Ctrl+C. This is an installation-free test on an already prepared PC;
the watcher still executes on that PC and will not resume after Windows restarts.
The board alone cannot request a browser launch through ordinary USB on an
unprepared computer. Windows AutoPlay handlers require host configuration; see
[Microsoft's AutoPlay documentation](https://learn.microsoft.com/en-us/windows/uwp/launch-resume/auto-launching-with-autoplay).

For a real plug-in test, close the tutor tab, shut the board down with
`sudo poweroff` in its terminal if USB is its power source, wait, then reconnect
the data cable. The temporary watcher should open the page after the board boots.
The application, model and database remain on the board. Only the watcher and
browser run on the PC. USB ports can differ from the Wi-Fi URL; use the URL printed
by the watcher, such as `http://127.0.0.1:7013`.

### One-time setup from the Arduino (Windows 10/11 x64)

The standalone setup package includes its Python runtime and ADB. Students do not
need Python, App Lab, internet access, or this repository. The prepared board
offers a **read-only MATHTUTOR USB drive** alongside its existing ADB and serial
interfaces. On each new computer/account:

1. Connect the Arduino with a data cable and wait for it to boot.
2. Open **This PC > MATHTUTOR > START.EXE**.
3. Click **Set up this computer** once. The browser opens when the tutor is ready.

After setup, the launcher starts when that Windows user signs in and opens the
browser after later connections. The board stores the model, problems and student
history; the PC stores only launcher configuration/logs and ordinary browser data.
First-time execution is manual: the Arduino does not bypass Windows approval or
force programs to run on an unprepared computer. This prototype is unsigned;
school-managed computers may require administrator approval. Do not disable their
security policies. macOS, Linux and Windows ARM installers are not provided.

Use **Start > Math Tutor** to reopen the notebook or turn off automatic opening.
Disabling removes only the tutor's login entry and stops its watcher. Its files
remain under `%LOCALAPPDATA%\KangarooTutor`; board notebooks are retained. Run
`START.EXE` again to enable it. The configured USB serial identifies this particular
board; create a package for each board when distributing additional units.

#### Build the setup package on the developer PC

Build on **Windows x64**, using an isolated environment with working Tk:

```powershell
python -m venv results/packaging-venv
results/packaging-venv/Scripts/python.exe -m pip install PyInstaller==6.22.0
results/packaging-venv/Scripts/python.exe laptop/build_windows_setup.py --serial BOARD_SERIAL
```

The builder locates ADB from App Lab or accepts `--adb PATH`. It bundles the three
ADB binaries plus license notices, Python/Tk/PyInstaller notices, and an immutable
versioned runtime. Build outputs stay in ignored `results/windows-setup/`:
`dist/START.exe`, a payload manifest, a 64 MiB `MATHTUTOR.img`, and checksums.
`results/windows-setup-latest.json` identifies the latest artifact. Build-time
downloads are separate from fully offline installation/use. The image is a regular
FAT16 file; this process never formats a PC disk or includes M3Kang/student data.

#### Enable the setup drive on the board once

Copy `MATHTUTOR.img` and `board/usb_setup_drive.py` to a new directory on the
**Arduino**. Verify the image SHA-256 against the build report. Keep working
Wi-Fi/SSH access during the first configuration, since USB briefly reconnects.
In the **board terminal**, run:

```bash
sudo python3 usb_setup_drive.py --install MATHTUTOR.img --sha256 IMAGE_SHA256
systemctl status math-tutor-usb-drive --no-pager
```

The installer validates the UNO Q identity, image and filesystem before changing
USB. It installs a dependent service after the existing `adbd.service`, keeps ADB
and serial, and adds only its own read-only mass-storage function. It enables
Microsoft OS descriptors for the ADB interface's WinUSB compatibility and changes
the USB device revision to refresh descriptor discovery. No vendor service or
model settings are edited. A failed attachment restores the recorded descriptors
and original USB binding. The image occupies 64 MiB on the board; model memory is
unaffected. A completely fresh Windows PC still needs a hardware validation pass.

To remove the setup drive on the **Arduino**, retaining the tutor and notebooks:

```bash
sudo python3 /usr/local/lib/math-tutor-usb/usb_setup_drive.py --uninstall
```

### Legacy persistent setup using existing Python/ADB

This developer-only alternative was **not** used for the earlier temporary USB
demonstration. Prefer the standalone package above for students. Do not install
both variants on the same account; they share the tutor's startup entry.

Start with a manual test on the **PC**:

```powershell
python laptop/usb_launcher.py open --serial BOARD_SERIAL
```

The launcher waits for that device, establishes an ADB forward, checks the app's
health/identity, then opens the default browser. It tries ports 7011–7020 if an
unrelated PC app already occupies 7011. It never kills that app or replaces
another device's port forward. Model warming/unavailability does not prevent
opening the application and its stored guidance.

Once that test works, install per-user automatic opening on the **PC**:

```powershell
python laptop/usb_launcher.py install --serial BOARD_SERIAL
```

This copies the launcher/configuration into `%LOCALAPPDATA%\KangarooTutor`, adds
its own named entry under the current user's Windows login startup settings, and
starts it without a console window. Python's existing `pythonw.exe` is used;
keep that Python installation and ADB available. No Python packages are installed.
The watcher opens the page once per USB connection, waits through board boot, and
opens it again after reconnection. The PC must be logged in and the helper running.

Logs are in `%LOCALAPPDATA%\KangarooTutor\launcher.log`. The helper does not handle
student answers, access the board database or perform model inference. A normal
practice request stays on the USB connection and board loopback.

Disable automatic opening on the **PC**:

```powershell
python laptop/usb_launcher.py uninstall
```

This removes only this launcher's login entry and signals its watcher to stop.
Configuration/logs remain for inspection. It does not remove ADB, Python, board
software or student history. To stop the app on the **board**:

```bash
sudo systemctl disable --now math-student
```

Before disconnecting board power, shut it down on the **board** with
`sudo poweroff` and wait. The launcher can be left installed for the next session.

## Integrated learning coach release

The `exp/slm-learning-coach` release retains the existing port, health identity and
standalone Windows launcher. Build/install with `--local-tutor --safe-shutdown` to
enable local conceptual explanations and the explicit saved-session power-off
control. Arithmetic uses Python; it works without an available model.

The installer now snapshots the existing SQLite notebook and service unit into
the new release's protected `install-backups/` directory before activation. It
also checks the previous release's training IDs and optional ML artifacts. A code
update that would remove them is rejected; obtain matching data and rebuild, or
use `--allow-data-change` only for an intentional dataset reduction. Existing
student progress is never included in a deployment archive.

See [SLM-COACH.md](../docs/SLM-COACH.md) for the complete student flow, teammate
handover, artifact limitations and hardware acceptance checks. The existing EXE
needs no rebuild for this UI update. First-use setup on a fresh Windows PC is
still required; automatic opening follows that one-time setup.

## Verification before the datathon demo

On the **PC**:

```powershell
python -m unittest laptop.test_usb_launcher -v
```

Automated checks cover readiness identity, unauthorized/other devices, opening
once, reconnects, port conflicts, preservation of unrelated forwards, archive
contents and service rendering. They do not prove USB drivers, systemd, model
latency, safe shutdown or Windows login startup on a real deployed setup.

On the **board**, verify service restart after reboot, the retained profile, short
hints with the model available and unavailable, and memory use with the full
stack. Then turn Wi-Fi off and confirm that the **PC** opens the app over USB and
that student answers update the board's database. Keep a rollback release path;
re-running its installer points the service back to that code while retaining data.
