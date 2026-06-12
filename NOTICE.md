# Required Notice

**Copyright © 2026 Wolfgang Sanyer**
Licensed under the Polyform Noncommercial License 1.0.0
https://polyformproject.org/licenses/noncommercial/1.0.0

---

## Project Information

**Project:** VendorScope, vendor readiness & availability analytics: a reusable data
pipeline and analysis engine for public vendor and licensing data. Flagship case study:
the Fayetteville Public Works Commission (PWC) vendor base.<br>
**Author / Owner:** Wolfgang Sanyer (personal portfolio project).

---

## Data Attribution

This project uses two publicly available source datasets (295 records each in the
Part-1 study). The raw files contain contact PII and are **not committed**. The Part-1
anonymized sample and its data dictionary were retired with the original pipeline
(both live in git history); the rebuilt pipeline regenerates them (see
[`docs/project-plan.md`](docs/project-plan.md)).

1. **Fayetteville PWC vendor list**
   - Source: Fayetteville Public Works Commission (eVP, `evp.nc.gov`)
   - License: public data
2. **Contractor license details**
   - Source: North Carolina Licensing Board for General Contractors (NCLBGC, `nclbgc.org`)
   - License: public data

The five PII columns (`Contact_Name`, `Contact_Email`, `Contact_Phone`, `Phone`,
`Qualifier_Name`) are removed from any published extract.

---

## Original Work

The data-cleaning-and-audit pipeline, the data-quality protocol, the analysis, and all
written materials are original work by the author, except where explicitly cited or
attributed to an external source.

---

## License Summary

This software is licensed for **non-commercial use only**. See [LICENSE](LICENSE) for the
full Polyform Noncommercial License 1.0.0 text and the Required Notice that must travel
with every copy.

### You MAY:

✅ Study the code and methodology<br>
✅ Use it for educational purposes<br>
✅ Share it with attribution<br>
✅ Modify it for personal learning

### You MAY NOT:

❌ Use it for commercial purposes<br>
❌ Sell the code or derivatives<br>
❌ Incorporate it into commercial products<br>
❌ Relicense under different terms

For commercial licensing inquiries, please contact the author.
