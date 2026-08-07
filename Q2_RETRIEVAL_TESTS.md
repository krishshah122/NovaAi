# Question 2: Retrieval Testing Evidence

This document contains the execution results of 5 diverse queries against the Pinecone Vector Database, demonstrating cross-lingual retrieval and accurate semantic matching as required by the Question 2 rubric.

---

### Query 1: Product Specifics
**User Question:** *"What is the exact deductible and out-of-pocket maximum for the Darwix AI Quantum Shield 2026 plan?"*

**Retrieved Record:**
- **Record ID:** `health_plan_quantum_shield`
- **Title:** Darwix AI Quantum Shield 2026 (Silver Plan)
- **Relevant Content:** "...The annual deductible is $1,427 for individuals and $2,854 for families. The out-of-pocket maximum is strictly capped at $4,900 for individuals and $9,800 for families..."
- **Source Reference:** `darwix_internal_product_docs_2026`

**Relevance Explanation:** The retriever correctly identified the specific product ID and extracted the exact financial parameters (deductibles and maximums) requested by the user, ignoring other generic health plans.
**Verdict:** Correct ✅

---

### Query 2: Policy & Eligibility
**User Question:** *"I missed open enrollment. Can I still get health insurance if I just moved to a new state?"*

**Retrieved Record:**
- **Record ID:** `supp_eligibility_marketplace`
- **Title:** Health Insurance Marketplace Eligibility Rules
- **Relevant Content:** "...Outside of Open Enrollment, you can sign up if you experience a qualifying life event: ... Moving to a new area with different plan options..."
- **Source Reference:** `healthcare.gov`

**Relevance Explanation:** The retriever accurately mapped the user's situation ("missed open enrollment" and "moved") to the semantic concept of a "Special Enrollment Period (SEP)" and "Qualifying Life Event".
**Verdict:** Correct ✅

---

### Query 3: Complex / Obscure Product
**User Question:** *"Are there any super cheap plans available if I am only 25 years old?"*

**Retrieved Record:**
- **Record ID:** `supp_plan_catastrophic`
- **Title:** Catastrophic Health Insurance Plan
- **Relevant Content:** "Catastrophic plans are a low-cost option available to people under 30... Very low monthly premiums... Eligibility requirements: Under 30 years old on the plan start date..."
- **Source Reference:** `healthcare.gov`

**Relevance Explanation:** The query contained no exact keyword matches (used "cheap" and "25 years old"), but the dense vector embeddings successfully linked it to "low-cost" and "under 30" in the Catastrophic plan record.
**Verdict:** Correct ✅

---

### Query 4: Tagalog (Philippines) Objection Handling
**User Question:** *"Gusto ko po sana kumuha ng insurance para sa pamilya ko, pero tight lang po ang budget namin ngayon dahil sa tuition ng mga bata."*

**Retrieved Record:**
- **Record ID:** `ph_objection_tight_budget`
- **Title:** Philippines Handling: Tight Budget Objection
- **Relevant Content:** "...I completely understand, Sir/Ma'am. Many of our clients with kids prioritize education too. However, think of this plan as protecting their future... For as low as 1,500 PHP a month—roughly the cost of your daily coffee—you can secure 1 Million PHP in coverage..."
- **Source Reference:** `darwix_ph_sales_playbook`

**Relevance Explanation:** Demonstrates native Taglish cross-lingual retrieval. The DB successfully fetched the highly localized Philippine sales playbook handling the exact objection of tight budgets.
**Verdict:** Correct ✅

---

### Query 5: Bahasa (Indonesia) Multifinance Product
**User Question:** *"Berapa lama maksimal tenor cicilan kalau saya mau ambil pembiayaan mobil bekas?"*

**Retrieved Record:**
- **Record ID:** `id_product_vehicle_financing`
- **Title:** Indonesia Vehicle Financing (Pembiayaan Kendaraan)
- **Relevant Content:** "...Tenor fleksibel mulai dari 12 bulan hingga maksimal 60 bulan (5 tahun) untuk mobil baru, dan maksimal 48 bulan (4 tahun) untuk mobil bekas..."
- **Source Reference:** `darwix_id_multifinance_guidelines`

**Relevance Explanation:** Demonstrates native Bahasa Indonesia retrieval. The user asked for maximum tenor for used cars ("mobil bekas"), and the chunk retrieved explicitly states 48 months for used cars.
**Verdict:** Correct ✅
