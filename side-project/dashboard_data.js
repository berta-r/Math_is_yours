// Populated automatically by Person 1's EDA script from index.db
window.DASHBOARD_DATA = {
  meta: {
    challengeName: "Repte Principal: Kangaroo Math Solver & Second Brain (Qualcomm + Arduino UNO Q)",
    challengeGoal: "Optimize accuracy and <11 tok/s edge latency across 1,466 Kangaroo problems in index.db",
    repoRef: "datathon-UPC-maths-qualcomm-arduino-unoq",
    projectScanned: null,     // e.g., "index.db + src/"
    lastScanTimestamp: null,  // e.g., "2026-11-14 16:30"
    activeQuestionId: "q4"
  },

  // Hardware profile for live UNO Q budget simulation (null fields populated by scan)
  hardwareProfile: {
    tokensPerSecond: 11,
    boardTimeoutSec: 25.0,
    medianPromptTokens: null, // e.g., 112
    p90PromptTokens: null     // e.g., 202 (Level 6-7 worst case)
  },

  // ===========================================================================
  // DIRECTED ISSUE -> BOTTLENECK -> EFFICIENT SOLUTION GRAPH (CRITERION 02)
  // ===========================================================================
  solutionGraph: {
    rationale: "02 Adequateness: Directed Causal Network — Connects index.db anomalies to UNO Q bottlenecks and highest-ROI code fixes",
    mostUrgentPathId: null,
    paths: []
  },

  // ===========================================================================
  // ACTIONABLE "WHAT TO DO NEXT" ENGINEERING QUEUE (EXECUTION CO-PILOT)
  // ===========================================================================
  nextActions: [
    // Populated dynamically from scan results. Expected shape:
    // {
    //   priority: "P1",
    //   questionId: "q4",
    //   title: "Enforce Dynamic RAG Token Cap on UNO Q",
    //   ownerRole: "Edge Inference Lead",
    //   targetFile: "src/rag_pipeline.py",
    //   triggerReason: "Level 6–7 prompts average 202 tokens (18.4s read time at 11 tok/s)",
    //   expectedImpact: "Eliminates timeouts on hard problems; saves 6.4s/query",
    //   codeSnippet: "# Ready-to-paste Python code using scanned parameters..."
    // }
  ],

  // ===========================================================================
  // 4 EDA & ARCHITECTURE QUESTIONS (TUKEY CRITERIA 01, 02, 03)
  // ===========================================================================
  questions: {
    q1: {
      prompt: "Do 384-D bge-small embeddings form discrete topic islands in UMAP space?",
      urgency: { rank: null, score: null, level: null, blockerNote: null },
      chartType: "scatter",
      chartRationale: "02 Adequateness: 2D UMAP Scatter — Exposes discrete semantic islands vs. continuous manifold across 1,466 embeddings",
      xLabel: "UMAP Dimension 1",
      yLabel: "UMAP Dimension 2",
      decisionDelta: {
        baselineLabel: "Cluster Silhouette Score",
        baselineValue: null,
        projectedLabel: "Selected Routing Algo",
        projectedValue: null,
        unit: "",
        recommendedAction: null
      },
      distribution: { min: null, median: null, max: null, outlierCount: null },
      chartData: { points: [] },
      evidence: [],
      verdict: null
    },
    q2: {
      prompt: "Do Kangaroo difficulty levels (0–7) progress smoothly across semantic space?",
      urgency: { rank: null, score: null, level: null, blockerNote: null },
      chartType: "scatter",
      chartRationale: "02 Adequateness: Level-Coded UMAP Scatter — Verifies spatial adjacency between consecutive difficulty tiers (Level k -> k+1)",
      xLabel: "UMAP Dimension 1",
      yLabel: "UMAP Dimension 2",
      decisionDelta: {
        baselineLabel: "k-NN Level Agreement (±1)",
        baselineValue: null,
        projectedLabel: "Prerequisite Graph",
        projectedValue: null,
        unit: "%",
        recommendedAction: null
      },
      distribution: { min: null, median: null, max: null, outlierCount: null },
      chartData: { points: [] },
      evidence: [],
      verdict: null
    },
    q3: {
      prompt: "How skewed is the A–E answer distribution vs. a 20% uniform baseline?",
      urgency: { rank: null, score: null, level: null, blockerNote: null },
      chartType: "bar",
      chartRationale: "02 Adequateness: Categorical Frequency Bar — Quantifies exact class imbalance across options A–E to calibrate debiasing priors",
      xLabel: "Correct Answer Label (A–E)",
      yLabel: "Training Set Share (%)",
      decisionDelta: {
        baselineLabel: "Peak Option Bias",
        baselineValue: null,
        projectedLabel: "Uniform Target Prior",
        projectedValue: null,
        unit: "%",
        recommendedAction: null
      },
      distribution: { min: null, median: null, max: null, outlierCount: null },
      chartData: { labels: ["A", "B", "C", "D", "E"], values: [] },
      evidence: [],
      verdict: null
    },
    q4: {
      prompt: "At which Kangaroo level does prompt length breach our 11 tok/s latency limit?",
      urgency: { rank: null, score: null, level: null, blockerNote: null },
      chartType: "line",
      chartRationale: "02 Adequateness: Ordered Level Trajectory + SLA Ceiling — Maps read latency at 11 tok/s across Levels 0–7 to set RAG token caps",
      xLabel: "Kangaroo Difficulty Level (0–7)",
      yLabel: "Est. Read Time at 11 tok/s (sec)",
      decisionDelta: {
        baselineLabel: "Level 7 Read Latency",
        baselineValue: null,
        projectedLabel: "Safe MAX_RAG_TOKENS",
        projectedValue: null,
        unit: " tok",
        recommendedAction: null
      },
      distribution: { min: null, median: null, max: null, outlierCount: null },
      chartData: {
        labels: ["Lvl 0", "Lvl 1", "Lvl 2", "Lvl 3", "Lvl 4", "Lvl 5", "Lvl 6", "Lvl 7"],
        values: [],
        limitLine: []
      },
      evidence: [],
      verdict: null
    }
  }
};