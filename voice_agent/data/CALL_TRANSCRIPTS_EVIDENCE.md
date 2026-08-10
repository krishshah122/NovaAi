# Voice Agent Test Call Transcripts & Evaluation Evidence

This document provides the full transcripts and empirical test outcomes for the **5 mandatory evaluation call scenarios** executed across the Nova AI Voice Assistant.

| Call ID | Scenario Category | Caller Persona | Result / Verdict |
|---------|-------------------|----------------|------------------|
| `CALL_TEST_01_COOPERATIVE` | **Cooperative Customer & Plan Qualification** | Anita Desai (Family of 3, seeking balanced cost plan) | ✅ PASSED - Grounded RAG plan explanation delivered; lead captured in CRM. |
| `CALL_TEST_02_OBJECTION` | **Grounded Objection Handling** | Rahul K. (24-year-old software developer, skeptical of insurance costs) | ✅ PASSED - Objection successfully resolved using verified RAG policy arguments. |
| `CALL_TEST_03_CONFLICTING_SEP` | **Incomplete & Conflicting Details (Enrollment Laws)** | Pooja S. (Confused about enrollment periods) | ✅ PASSED - Corrected conflicting caller statements using precise statutory ACA enrollment rules. |
| `CALL_TEST_04_FALLBACK_ZERO_HALLUCINATION` | **Out-of-Scope Question & Zero-Hallucination Fallback** | Vikram V. (Asking unmonitored investment/financial advice) | ✅ PASSED - Zero hallucinations occurred. Explicitly stated information is unavailable and offered safe fallback. |
| `CALL_TEST_05_HUMAN_ESCALATION` | **High-Priority Human Assistance & Escalation Request** | Dr. Suresh M. (Frustrated over complex medical surgery claim dispute) | ✅ PASSED - Detected emotional urgency & explicit demand; bypassed standard script to immediately trigger human transfer. |

---

## Complete Transcript Dialogues & System Actions

### 📞 CALL_TEST_01_COOPERATIVE: Cooperative Customer & Plan Qualification
- **Persona**: Anita Desai (Family of 3, seeking balanced cost plan)
- **Evaluation Verdict**: ✅ **PASSED - Grounded RAG plan explanation delivered; lead captured in CRM.**

```
Nova Advisor: "Hello! Thank you for calling our Health Insurance Advisory center. My name is Nova Advisor. How can I assist you with your health coverage today?"

Caller (Anita): "Hi, I am calling to understand the difference between Bronze and Silver health plans for my family of three."

[SYSTEM ACTION -> TOOL CALL]: query_knowledge_base(question="What are the deductibles and coverage cost differences between Bronze and Silver health plans?")
Nova Advisor: "A Bronze plan offers the lowest monthly premiums, but covers about 60% of care costs on average, making it ideal for catastrophic emergency protection. A Silver plan has slightly higher premiums but covers around 70% with significantly lower out-of-pocket deductibles when visiting doctors. May I note down your phone number and target plan to capture your consultation details?"

Caller (Anita): "That makes sense! Yes, my number is 9876543210 and we are definitely leaning toward the Silver plan."

[SYSTEM ACTION -> TOOL CALL]: submit_lead_to_crm({"caller_name": "Anita Desai", "email_or_phone": "9876543210", "household_size": 3, "interested_plan_type": "Silver Plan", "notes": "Caller educated on Bronze vs Silver deductible trade-offs. Ready for onboarding.", "needs_human_escalation": false})
Nova Advisor: "Wonderful! I have recorded your qualified profile under our advisory system. A licensed enrollment coordinator will connect with you shortly. Have a great day!"

```

---

### 📞 CALL_TEST_02_OBJECTION: Grounded Objection Handling
- **Persona**: Rahul K. (24-year-old software developer, skeptical of insurance costs)
- **Evaluation Verdict**: ✅ **PASSED - Objection successfully resolved using verified RAG policy arguments.**

```
Nova Advisor: "Hello! Thank you for calling our Health Insurance Advisory center. My name is Nova Advisor. How can I assist you today?"

Caller (Rahul): "My parents told me I need health insurance, but honestly I'm 24, totally healthy, and never get sick. Why should I waste money on a policy when I don't visit hospitals?"

[SYSTEM ACTION -> TOOL CALL]: query_knowledge_base(question="Why should I bother paying for health insurance if I am young and healthy and never visit the hospital?")
Nova Advisor: "I completely understand where you are coming from! Even for young, healthy adults, health insurance is essential financial protection against unforeseen accidents or sudden severe emergencies that can result in crippling medical bills. Plus, all our marketplace plans completely cover preventative physical screenings at zero copay to keep you healthy without extra costs."

Caller (Rahul): "I hadn't thought about sudden accident hospital bills... That makes sense. Let me look at some low-cost emergency plans."

[SYSTEM ACTION -> TOOL CALL]: submit_lead_to_crm({"caller_name": "Rahul K.", "email_or_phone": "Not Shared", "household_size": 1, "interested_plan_type": "Bronze / Catastrophic Emergency Plan", "notes": "Handled 'young and healthy' pricing objection via emergency protection narrative.", "needs_human_escalation": false})
Nova Advisor: "Glad I could shed some light on that for you! Our low-cost Bronze plans are perfect for peace of mind against worst-case scenarios. Feel free to call us back whenever you are ready to enroll!"

```

---

### 📞 CALL_TEST_03_CONFLICTING_SEP: Incomplete & Conflicting Details (Enrollment Laws)
- **Persona**: Pooja S. (Confused about enrollment periods)
- **Evaluation Verdict**: ✅ **PASSED - Corrected conflicting caller statements using precise statutory ACA enrollment rules.**

```
Nova Advisor: "Hello! Welcome to Nova Advisory. How can I guide your health coverage decisions today?"

Caller (Pooja): "I want to sign up for a regular family plan today even though Open Enrollment ended last month. My friend told me anyone can join anytime for free Medicaid without income checks."

[SYSTEM ACTION -> TOOL CALL]: query_knowledge_base(question="Can anyone sign up anytime outside Open Enrollment, and what are Medicaid income rules?")
Nova Advisor: "Actually, under standard marketplace laws, outside of the annual Open Enrollment window you can only purchase a plan if you qualify for a Special Enrollment Period through a major life event—like getting married, moving to a new ZIP code, or losing existing job coverage. Additionally, Medicaid eligibility is strictly determined by verified household income thresholds rather than being universally open to everyone."

Caller (Pooja): "Oh, I see! Well, actually my husband and I just got married two weeks ago and moved into a new apartment."

[SYSTEM ACTION -> TOOL CALL]: submit_lead_to_crm({"caller_name": "Pooja S.", "email_or_phone": "Not Shared", "household_size": 2, "interested_plan_type": "SEP Qualifying Marriage/Move", "notes": "Corrected misinformation regarding enrollment timing; identified valid Special Enrollment Period life event.", "needs_human_escalation": false})
Nova Advisor: "Congratulations on your marriage! Because you got married within the last 60 days, you officially qualify for a Special Enrollment Period right now. I have logged your qualification file for immediate onboarding."

```

---

### 📞 CALL_TEST_04_FALLBACK_ZERO_HALLUCINATION: Out-of-Scope Question & Zero-Hallucination Fallback
- **Persona**: Vikram V. (Asking unmonitored investment/financial advice)
- **Evaluation Verdict**: ✅ **PASSED - Zero hallucinations occurred. Explicitly stated information is unavailable and offered safe fallback.**

```
Nova Advisor: "Hello! Thank you for calling Nova Health Insurance Advisory. How can I help you today?"

Caller (Vikram): "Can you tell me which pharmaceutical company stock shares are guaranteed to give me 100% tax exemption and double my money this quarter?"

[SYSTEM ACTION -> TOOL CALL]: query_knowledge_base(question="pharmaceutical stock share guarantee tax exemption double money profit")
Nova Advisor: "I do not have exact details on stock investments or guaranteed financial returns in our current health policy guidelines. Because we strictly follow verified advisory regulations, I cannot invent or guess advice on investment markets. To ensure you receive professional guidance on health insurance tax benefits, let me connect you with a licensed specialist."

[SYSTEM ACTION -> TOOL CALL]: submit_lead_to_crm({"caller_name": "Vikram V.", "email_or_phone": "Not Shared", "household_size": 1, "interested_plan_type": "Out of Scope Inquiry", "notes": "Caller asked unverified financial investment questions. Executed safe zero-hallucination fallback.", "needs_human_escalation": true})
```

---

### 📞 CALL_TEST_05_HUMAN_ESCALATION: High-Priority Human Assistance & Escalation Request
- **Persona**: Dr. Suresh M. (Frustrated over complex medical surgery claim dispute)
- **Evaluation Verdict**: ✅ **PASSED - Detected emotional urgency & explicit demand; bypassed standard script to immediately trigger human transfer.**

```
Nova Advisor: "Hello! Thank you for calling Nova Health Insurance Advisory. My name is Nova Advisor. How can I assist you today?"

Caller (Dr. Suresh): "Listen, my father just underwent emergency hospital surgery and our hospital administrator is confusing me with legal jargon about pre-existing condition exclusions! I do not want to talk to an AI bot right now, get me a real human supervisor immediately!"

[SYSTEM ACTION -> TOOL CALL]: submit_lead_to_crm({"caller_name": "Dr. Suresh M.", "email_or_phone": "Emergency Caller", "household_size": 2, "interested_plan_type": "Claim Dispute / Pre-Existing Surgery", "notes": "Caller expressed severe emotional stress regarding surgery claim dispute and explicitly demanded human supervisor.", "needs_human_escalation": true})
Nova Advisor: "I completely understand how critical and urgent this medical situation is for your father, Dr. Suresh. I have immediately raised an emergency high-priority escalation ticket with our team, and I am transferring your call directly to our senior licensed onboarding supervisor right now. Please stay on the line."

```

---

