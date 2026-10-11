export const STRINGS = {
  app: {
    title: "Watt & Where",
    subtitle: "Understand your apartment's common-area electricity bill",
    eyebrow: "Apartment electricity insights",
    demoBanner: "Demo with sample data. Figures are estimates.",
    offlineBanner:
      "Saved example from a live run. Run it yourself: see the README.",
    offlineLabel: "Offline snapshot",
    footer:
      "Sample data. Estimates only. Always check equipment in person.",
    committeeLink: "Committee view (preview)",
    dashboardLink: "Back to dashboard",
    textSize: "Text size",
    smaller: "Smaller",
    normal: "Normal",
    larger: "Larger",
  },

  dashboard: {
    // General page
    intro:
      "Understand your apartment's common-area electricity use and find months worth checking.",
    loading: "Reading your bills...",
    retry: "Try again",
    runAnalysis: "Run analysis",
    createSummary: "Create summary",
    openReport: "Open full report",
    copySummary: "Copy summary",
    copied: "Copied",
    showNumbers: "Show numbers",
    hideNumbers: "Hide numbers",
    previousMonth: "Previous month",
    nextMonth: "Next month",
    goToFlaggedMonth: "Go to flagged month",
    viewFlaggedMonth: "View flagged month",
    shortAnswer: "The short answer",
    latestMonth: "Latest month",
    selectedMonth: "Selected month",
    billEyebrow: "Monthly electricity use",
    billTitle: "How your electricity use changes",
    billDescription:
      "Select a month to see its electricity use and estimated breakdown.",
    chartInstruction:
      "Select a bar to read that month's details below.",
    chartTextAlternative: "Read monthly values as a list",
    chartComingNext: "Monthly electricity use",
    noChartData: "Monthly bill data is not available yet.",
    actualUnits: "Actual electricity use",
    estimatedUnits: "Estimated electricity use",
    unexplainedUnits: "Not accounted for",
    billAmount: "Bill amount",
    sameMonthLastYear: "Change from the same month last year",
    notAvailable: "Not available",
    statusLabel: "Status",
    flagged: "Needs attention",
    check: "Worth checking",
    steady: "Looks steady",
    kwhExplanation:
      "One unit of electricity equals 1 kWh, which is what your electricity bill counts.",
    breakdownTitle: "Where the electricity may be going",
    breakdownDescription:
      "These are estimates based on available information, not direct measurements for each category.",
    notAccountedFor: "Not accounted for",
    notAccountedForHelp:
      "Electricity our estimate could not assign to listed equipment.",

    // Headline states
    noAnalysisTitle: "Let's look at your bills",
    noAnalysisMessage:
      "Your electricity insights will appear here once your bills have been analysed.",
    normalHeadline:
      "Your latest bill looks normal compared with usual patterns.",
    normalTitle: "Your electricity use looks steady",
    normalMessage:
      "No major unusual change was flagged for {month}.",
    alertTitle: "Your electricity use needs a closer look",
    alertMessage: "We found an unusual change in {month}.",
    alertMessageWithSaving:
      "We found an unusual change in {month}. Reviewing it could help save around {saving} per month.",
    watchTitle: "One month is worth checking",
    watchMessage:
      "Some electricity use in {month} looks different from usual.",
    higherThanExpected: "Higher than expected",
    extraUnits: "Extra units",
    extraCost: "Extra cost",

    // Evidence
    evidenceEyebrow: "What we found",
    evidenceTitle: "Why this month was flagged",
    evidenceMonth:
      "The electricity use for {month} was flagged for review.",
    referenceMonth: "Comparison month",
    pumpEvidenceTitle: "Pump operating time",
    possibleReasonsTitle: "Possible reasons to investigate",
    evidenceItem: "Possible explanation",
    evidenceLimit: "Please keep in mind:",
    evidenceCaveat:
      "A flagged month is a reason to investigate. It does not, by itself, prove that equipment is faulty or that electricity was wasted.",

    // Recommended actions
    actionsEyebrow: "What you can do",
    actionsTitle: "Recommended next steps",
    noActions: "There are no specific actions to show for this month.",
    actionItem: "Recommended action",
    checklistNote:
      "Tick an item when your apartment team has reviewed it.",
    actionsReviewed: "reviewed",

    // Summary
    summaryEyebrow: "Your report",
    summaryTitle: "Electricity summary",
    noSummary: "No saved summary is available in this example.",
    summaryBedrock: "AI-generated summary",
    summaryFallback: "Standard template",
    fallbackSummary: "Standard template",
    aiChecked: "Written by AI and number-checked",

    // Report
    reportTitle: "Full report",
    reportDescription:
      "Open the saved example report for a more detailed view.",
    reportSampleLabel: "Open the saved example report",
    liveReportNote:
      "Report generation is available in the configured live version.",

    // Text size
    textSizeLabel: "Text size",

    // How it works
    howItWorks: "How it works",
    howItWorksText:
      "We estimate where the electricity should go, compare each month with usual patterns and the same month last year, and rank likely causes. The summary wording is written by AI, but every number comes from our calculations.",
    methodNote:
      "Detection uses transparent statistics, not machine learning.",

    // Evidence strength
    strongEvidence: "Strong evidence",
    someEvidence: "Some evidence",
    weakEvidence: "Weak evidence",
    technicalDetails: "Technical details",

    // Offline mode
    availableInLiveVersion:
      "Available in the live version (see the README)",
    offlineActionNote:
      "Available in the live version (see the README).",
  },

  errors: {
    access: "Access problem. Please check the app's setup.",
    throttled:
      "Too many requests. Please wait a moment and try again.",
    server:
      "We couldn't reach the server. Please try again.",
    snapshot:
      "We couldn't read the saved example. Check that demo-snapshot.json exists and try again.",
    analysisMissing: "Let's look at your bills",
  },

  committee: {
    title: "Equipment list",
    helper:
      "Add the pumps, lifts, lights and other machines that use electricity. Use the numbers on the machine's nameplate.",
    previewBanner:
      "Preview only. Nothing here is saved or sent anywhere.",
    addEquipment: "Add equipment",
    remove: "Remove",
    reset: "Reset to sample list",
    save: "Save appliances",
    saveMessage:
      "Preview only: your changes were not saved. In the full version, saving would update your analysis.",
    removePrompt: "Remove this item?",
    yes: "Yes, remove",
    no: "No, keep it",
    unsaved: "Unsaved changes",
    estimate: "Estimated use",
    totalEstimate: "All equipment",
    roughEstimate:
      "Rough estimate based on power, quantity, and daily hours.",
    fullVersionNote:
      "In the full version, only the committee can edit this list; residents see the results.",
    name: "Equipment name",
    type: "Equipment type",
    quantity: "Quantity",
    power: "Power rating",
    hours: "Hours per day",
    control: "Control type",
    addSomethingElse: "Something else",
    invalidName: "Enter an equipment name.",
    invalidQuantity:
      "Quantity must be a whole number greater than zero.",
    invalidPower: "Power rating must be greater than zero.",
    invalidHours: "Hours must be between 0 and 24.",
    invalidType: "Choose an equipment type.",
    invalidControl: "Choose a control type.",
    confirmReset: "Reset all changes to the sample list?",
    savedLocallyNote:
      "Changes stay on this page only and disappear when you leave.",
  },

  categories: {
    pump: "Pumps",
    lift: "Lifts",
    stp: "Sewage treatment plant",
    waterTreatment: "Water treatment",
    water_treatment: "Water treatment",
    lighting: "Lights",
  },

  controls: {
    pressure_switch: "Pressure switch",
    timer: "Timer",
    manual: "Manual",
    none: "None",
  },
};

export function formatMonth(value) {
  if (!value) return "Unknown month";

  const date = /^\d{4}-\d{2}$/.test(value)
    ? new Date(`${value}-01T12:00:00`)
    : new Date(value);

  if (Number.isNaN(date.getTime())) return String(value);

  return new Intl.DateTimeFormat("en-IN", {
    month: "long",
    year: "numeric",
  }).format(date);
}

export function formatRupees(value) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "Not available";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function formatUnits(value) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "Not available";
  }

  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function confidenceLabel(value) {
  const labels = {
    High: STRINGS.dashboard.strongEvidence,
    Medium: STRINGS.dashboard.someEvidence,
    Low: STRINGS.dashboard.weakEvidence,
  };

  return labels[value] ?? STRINGS.dashboard.weakEvidence;
}