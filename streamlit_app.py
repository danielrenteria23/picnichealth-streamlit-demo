"""
PicnicHealth Study Eligibility Screener — Streamlit + Claude API Demo

This is a working example of the kind of internal tool a Forward Deployed AI Engineer
would build. A study coordinator uploads a patient record (or pastes text), selects
a study protocol, and gets an AI-powered eligibility assessment in seconds.

Run with: streamlit run app.py
Deploy with: streamlit community cloud, Railway, or any Docker host
"""

import streamlit as st
import json
import os

# ──────────────────────────────────────────────
# Try to import anthropic; if not available or no API key, use mock mode
# ──────────────────────────────────────────────
MOCK_MODE = True
_init_error = None
try:
    import anthropic

    # Check Streamlit Cloud secrets first, then env vars
    api_key = None
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
        MOCK_MODE = False
    else:
        _init_error = "No API key found in secrets or environment variables."
except ImportError:
    _init_error = "anthropic package not installed."
except Exception as e:
    _init_error = f"Error initializing Claude client: {e}"

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Study Eligibility Screener",
    page_icon="🏥",
    layout="wide"
)

# ──────────────────────────────────────────────
# Study protocols (in real life, these come from a database)
# ──────────────────────────────────────────────
PROTOCOLS = {
    "Diabetes Phase III — GLYCO-2026": {
        "description": "Evaluating novel GLP-1 receptor agonist for T2DM patients with inadequate glycemic control",
        "criteria": [
            {"id": "AGE", "text": "Age 18–65 years", "type": "inclusion"},
            {"id": "HBA1C", "text": "HbA1c between 7.5% and 11.0% at screening", "type": "inclusion"},
            {"id": "T2DM", "text": "Confirmed diagnosis of Type 2 Diabetes Mellitus", "type": "inclusion"},
            {"id": "EGFR", "text": "eGFR ≥ 30 mL/min/1.73m²", "type": "inclusion"},
            {"id": "BMI", "text": "BMI between 25 and 45 kg/m²", "type": "inclusion"},
            {"id": "GLP1", "text": "No prior use of GLP-1 receptor agonists (Ozempic, Trulicity, etc.)", "type": "exclusion"},
            {"id": "INSULIN", "text": "Not currently on insulin therapy", "type": "exclusion"},
            {"id": "CARDIAC", "text": "No history of major cardiac events in past 6 months", "type": "exclusion"},
            {"id": "LIVER", "text": "ALT/AST < 3x upper limit of normal", "type": "inclusion"},
            {"id": "PREGNANCY", "text": "Not pregnant or planning pregnancy during study period", "type": "exclusion"},
        ]
    },
    "Cardiology RWE Study — HEART-SAFE": {
        "description": "Real-world evidence study for novel anticoagulant in atrial fibrillation patients",
        "criteria": [
            {"id": "AGE", "text": "Age ≥ 18 years", "type": "inclusion"},
            {"id": "AFIB", "text": "Confirmed diagnosis of non-valvular atrial fibrillation", "type": "inclusion"},
            {"id": "CHADS", "text": "CHA₂DS₂-VASc score ≥ 2", "type": "inclusion"},
            {"id": "BLEED", "text": "No active bleeding or bleeding disorder", "type": "exclusion"},
            {"id": "RENAL", "text": "CrCl ≥ 15 mL/min", "type": "inclusion"},
            {"id": "ANTICOAG", "text": "Currently on or initiating oral anticoagulant therapy", "type": "inclusion"},
            {"id": "VALVE", "text": "No mechanical heart valve or moderate-severe mitral stenosis", "type": "exclusion"},
            {"id": "SURGERY", "text": "No planned major surgery within 3 months", "type": "exclusion"},
        ]
    }
}

# ──────────────────────────────────────────────
# Sample patient record (for demo purposes)
# ──────────────────────────────────────────────
SAMPLE_RECORD = """PATIENT MEDICAL RECORD SUMMARY
================================
Patient: Jane Martinez, DOB: 06/15/1978 (Age 47)
MRN: PH-2026-04892

DIAGNOSES:
- Type 2 Diabetes Mellitus (E11.9), diagnosed 2019
- Hypertension (I10), diagnosed 2021
- Obesity (E66.01), BMI 32.4 kg/m²

CURRENT MEDICATIONS:
- Metformin 1000mg BID
- Lisinopril 20mg daily
- Atorvastatin 40mg daily

RECENT LAB RESULTS (01/15/2026):
- HbA1c: 8.2%
- Fasting glucose: 167 mg/dL
- eGFR: 72 mL/min/1.73m²
- ALT: 28 U/L (normal range: 7-56)
- AST: 31 U/L (normal range: 10-40)
- Creatinine: 0.9 mg/dL
- Total cholesterol: 198 mg/dL

MEDICAL HISTORY:
- No prior GLP-1 receptor agonist use
- No insulin therapy
- Appendectomy (2005)
- No history of cardiac events
- No history of stroke or TIA

SOCIAL HISTORY:
- Non-smoker
- Moderate alcohol use (2-3 drinks/week)
- Not pregnant, postmenopausal

RECENT VISITS:
- 01/15/2026: Routine follow-up with PCP Dr. Sarah Chen
  Notes: "Patient reports difficulty managing blood sugar with current regimen.
  Discussed intensifying therapy. Patient interested in clinical trial options.
  Consider GLP-1 agonist or SGLT2 inhibitor if trial not available."

- 11/20/2025: Endocrinology consult with Dr. James Park
  Notes: "A1c trending up from 7.8 to 8.2 over 6 months despite max metformin.
  BMI stable at 32.4. Would benefit from additional agent targeting both
  glycemic control and weight management."
"""


def get_mock_assessment(criteria: list[dict]) -> list[dict]:
    """Return a realistic mock assessment when no API key is available."""
    mock_results = {
        "AGE": {"status": "MET", "confidence": "HIGH",
                "evidence": "Patient DOB 06/15/1978, age 47. Within 18-65 range.",
                "source": "Demographics section"},
        "HBA1C": {"status": "MET", "confidence": "HIGH",
                  "evidence": "HbA1c: 8.2% as of 01/15/2026. Within 7.5%-11.0% range.",
                  "source": "Lab results, 01/15/2026"},
        "T2DM": {"status": "MET", "confidence": "HIGH",
                 "evidence": "Confirmed diagnosis: Type 2 Diabetes Mellitus (E11.9), diagnosed 2019.",
                 "source": "Diagnoses section"},
        "EGFR": {"status": "MET", "confidence": "HIGH",
                 "evidence": "eGFR: 72 mL/min/1.73m². Above threshold of 30.",
                 "source": "Lab results, 01/15/2026"},
        "BMI": {"status": "MET", "confidence": "HIGH",
                "evidence": "BMI 32.4 kg/m². Within 25-45 range.",
                "source": "Diagnoses section"},
        "GLP1": {"status": "MET", "confidence": "MEDIUM",
                 "evidence": "Record states 'No prior GLP-1 receptor agonist use.' Current meds list shows Metformin, Lisinopril, Atorvastatin only. However, full pharmacy history not available.",
                 "source": "Medical history + Medications"},
        "INSULIN": {"status": "MET", "confidence": "HIGH",
                    "evidence": "No insulin in current medications. Record confirms 'No insulin therapy.'",
                    "source": "Current medications + Medical history"},
        "CARDIAC": {"status": "MET", "confidence": "MEDIUM",
                    "evidence": "Record states 'No history of cardiac events.' No cardiac diagnoses listed. Note: only covers documented history at this facility.",
                    "source": "Medical history"},
        "LIVER": {"status": "MET", "confidence": "HIGH",
                  "evidence": "ALT: 28 U/L, AST: 31 U/L. Both well within normal range and below 3x ULN.",
                  "source": "Lab results, 01/15/2026"},
        "PREGNANCY": {"status": "MET", "confidence": "HIGH",
                      "evidence": "Patient is postmenopausal per social history. Not pregnant.",
                      "source": "Social history"},
        "AFIB": {"status": "NOT_MET", "confidence": "HIGH",
                 "evidence": "No diagnosis of atrial fibrillation found in record.",
                 "source": "Diagnoses section"},
        "CHADS": {"status": "UNCERTAIN", "confidence": "LOW",
                  "evidence": "Unable to calculate CHA₂DS₂-VASc score — no AF diagnosis documented.",
                  "source": "N/A"},
        "BLEED": {"status": "MET", "confidence": "MEDIUM",
                  "evidence": "No bleeding disorders documented. No anticoagulant use.",
                  "source": "Medical history"},
        "RENAL": {"status": "MET", "confidence": "HIGH",
                  "evidence": "Creatinine 0.9 mg/dL, eGFR 72 — well above 15 mL/min threshold.",
                  "source": "Lab results"},
        "ANTICOAG": {"status": "NOT_MET", "confidence": "HIGH",
                     "evidence": "Patient not on any anticoagulant therapy.",
                     "source": "Current medications"},
        "VALVE": {"status": "MET", "confidence": "MEDIUM",
                  "evidence": "No valvular heart disease documented.",
                  "source": "Medical history"},
        "SURGERY": {"status": "UNCERTAIN", "confidence": "LOW",
                    "evidence": "No planned surgeries documented, but future plans not always recorded.",
                    "source": "N/A"},
    }

    results = []
    for c in criteria:
        cid = c["id"]
        if cid in mock_results:
            results.append({**c, **mock_results[cid]})
        else:
            results.append({**c, "status": "UNCERTAIN", "confidence": "LOW",
                           "evidence": "No relevant information found in record.",
                           "source": "N/A"})
    return results


def get_claude_assessment(record_text: str, criteria: list[dict]) -> list[dict]:
    """Call Claude API to assess patient eligibility against study criteria."""
    criteria_text = "\n".join(
        f"- [{c['id']}] ({c['type']}): {c['text']}" for c in criteria
    )

    prompt = f"""You are a clinical research screening assistant. Analyze this patient record
against the study eligibility criteria below.

For EACH criterion, return a JSON object with:
- "id": the criterion ID
- "status": "MET" | "NOT_MET" | "UNCERTAIN"
- "confidence": "HIGH" | "MEDIUM" | "LOW"
- "evidence": a 1-2 sentence explanation citing specific data from the record
- "source": which section of the record the evidence came from

IMPORTANT: Be conservative. If the record doesn't contain enough information to confirm
a criterion, mark it UNCERTAIN. Always cite specific values or quotes.

PATIENT RECORD:
{record_text}

ELIGIBILITY CRITERIA:
{criteria_text}

Return ONLY a JSON array of objects. No other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        st.error(f"Claude API call failed: {e}")
        return get_mock_assessment(criteria)

    raw_text = response.content[0].text

    # Strip markdown code fences if Claude wraps the JSON
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[1:])  # drop first ```json line
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        results_raw = json.loads(cleaned)
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse Claude response as JSON: {e}")
        st.code(raw_text[:1000], language="text")
        return get_mock_assessment(criteria)

    # Merge with original criteria data
    results = []
    for c in criteria:
        match = next((r for r in results_raw if r["id"] == c["id"]), None)
        if match:
            results.append({**c, **match})
        else:
            results.append({**c, "status": "UNCERTAIN", "confidence": "LOW",
                           "evidence": "Not evaluated", "source": "N/A"})
    return results


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
st.title("🏥 Study Eligibility Screener")
st.caption("AI-powered patient screening for clinical research studies")

if MOCK_MODE:
    msg = "🔧 **Demo Mode** — Running with mock AI responses."
    if _init_error:
        msg += f" Reason: {_init_error}"
    else:
        msg += " Set ANTHROPIC_API_KEY in Streamlit secrets to use Claude."
    st.info(msg, icon="ℹ️")
else:
    st.success("✅ **Live Mode** — Connected to Claude API.", icon="✅")

# Sidebar: study selection
with st.sidebar:
    st.header("Study Protocol")
    selected_study = st.selectbox(
        "Select study",
        options=list(PROTOCOLS.keys())
    )
    protocol = PROTOCOLS[selected_study]
    st.caption(protocol["description"])

    st.divider()
    st.subheader("Criteria Summary")
    inclusions = [c for c in protocol["criteria"] if c["type"] == "inclusion"]
    exclusions = [c for c in protocol["criteria"] if c["type"] == "exclusion"]
    st.write(f"**Inclusion:** {len(inclusions)} criteria")
    st.write(f"**Exclusion:** {len(exclusions)} criteria")

# Main area: patient record input
tab1, tab2 = st.tabs(["📋 Paste Record", "📄 Upload File"])

with tab1:
    record_text = st.text_area(
        "Paste patient record text",
        value=SAMPLE_RECORD,
        height=300,
        help="Paste clinical notes, lab results, or any patient documentation"
    )

with tab2:
    uploaded = st.file_uploader("Upload patient record", type=["txt", "pdf", "csv"])
    if uploaded:
        record_text = uploaded.read().decode("utf-8", errors="replace")
        st.text_area("Uploaded content preview", value=record_text[:2000], height=200, disabled=True)

# Screen button
st.divider()

if st.button("🔍 Screen Patient", type="primary", use_container_width=True):
    with st.spinner("Analyzing patient record against protocol criteria..."):
        if MOCK_MODE:
            results = get_mock_assessment(protocol["criteria"])
        else:
            results = get_claude_assessment(record_text, protocol["criteria"])

    # ── Results summary ──
    met = [r for r in results if r["status"] == "MET"]
    not_met = [r for r in results if r["status"] == "NOT_MET"]
    uncertain = [r for r in results if r["status"] == "UNCERTAIN"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Criteria", len(results))
    col2.metric("✅ Met", len(met))
    col3.metric("❌ Not Met", len(not_met))
    col4.metric("⚠️ Needs Review", len(uncertain))

    # Overall recommendation
    if len(not_met) > 0:
        st.error(f"**LIKELY INELIGIBLE** — {len(not_met)} criteria not met. Review details below.")
    elif len(uncertain) > 0:
        st.warning(f"**NEEDS REVIEW** — All assessed criteria met, but {len(uncertain)} require human verification.")
    else:
        st.success("**LIKELY ELIGIBLE** — All criteria appear to be met. Recommend proceeding to enrollment.")

    # ── Detailed results ──
    st.subheader("Detailed Assessment")

    for r in results:
        icon = {"MET": "✅", "NOT_MET": "❌", "UNCERTAIN": "⚠️"}[r["status"]]
        conf_color = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}[r["confidence"]]
        type_badge = "🟦 Inclusion" if r["type"] == "inclusion" else "🟥 Exclusion"

        with st.expander(f"{icon} [{r['id']}] {r['text']}", expanded=(r["status"] != "MET")):
            st.write(f"**Type:** {type_badge}")
            st.write(f"**Status:** {r['status']} | **Confidence:** {conf_color} {r['confidence']}")
            st.write(f"**Evidence:** {r['evidence']}")
            st.write(f"**Source:** {r['source']}")

    # ── Action buttons ──
    st.divider()
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("✅ Approve for Enrollment", use_container_width=True):
            st.success("Patient flagged for enrollment. Study coordinator notified.")

    with col_b:
        if st.button("⚠️ Flag for Manual Review", use_container_width=True):
            st.info("Patient flagged for manual review. Added to review queue.")

    with col_c:
        if st.button("❌ Mark Ineligible", use_container_width=True):
            st.warning("Patient marked ineligible. Reason logged.")

    # ── Export ──
    st.divider()
    export_data = json.dumps(results, indent=2)
    st.download_button(
        "📥 Export Assessment as JSON",
        data=export_data,
        file_name=f"eligibility_{selected_study.split('—')[1].strip()}.json",
        mime="application/json"
    )
