window.DASHBOARD_DATA = {
  meta: {
    projectScanned: null, // e.g., "src/engine"
    activeQuestionId: "q1",
    lastScanTimestamp: null
  },
  // Each question maps to specific scanned parameters & the most adequate chart type
  questions: {
    q1: {
      prompt: "Where is our highest technical or operational bottleneck?",
      chartType: "bar", // Adequate for ranking modules/components
      kpis: [
        { label: "Max Complexity / Load", value: null, suffix: " pts" },
        { label: "Coupling Density", value: null, suffix: "%" },
        { label: "Critical Hotspots", value: null, suffix: " files" }
      ],
      chartData: {
        labels: [], // e.g., ["auth.py", "parser.py", "sync.py"]
        values: []  // e.g., [84, 32, 61]
      },
      evidence: [], // e.g., [{ file: "auth.py", line: 42, parameter: "Nested depth = 6" }]
      verdict: null // Auto-populated by your scanner's decision rule
    },
    q2: {
      prompt: "Which optimization gives the highest impact for the lowest effort?",
      chartType: "scatter", // Adequate for 2-variable trade-offs (Effort vs. Gain)
      kpis: [
        { label: "Best ROI Target", value: null },
        { label: "Est. Effort Score", value: null, suffix: "/100" },
        { label: "Projected Gain", value: null, suffix: "%" }
      ],
      chartData: {
        points: [] // e.g., [{ label: "Cache Layer", x: 20, y: 88 }]
      },
      evidence: [],
      verdict: null
    }
  }
};