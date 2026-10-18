"""Evidence-linked assessment; severity increases with documented problems.

This automates working papers, not consultant judgment or a readiness certification.
"""
from decimal import Decimal

from .money import money

DOMAINS = ("operations", "finance", "systems", "automation_ai", "security_risk")


def assess(findings):
    ids, result = set(), []
    for f in findings:
        if f["finding_id"] in ids:
            raise ValueError("Duplicate finding ID")
        ids.add(f["finding_id"])
        if f["domain"] not in DOMAINS or type(f["severity"]) is not int or not 1<=f["severity"]<=5:
            raise ValueError("Invalid domain or severity")
        if f["confidence"] not in {"high","medium","low"}:
            raise ValueError("Invalid confidence")
        for key in ("finding_id","symptom","root_cause","treatment","owner"):
            if not isinstance(f[key],str) or not f[key].strip():
                raise ValueError("Missing narrative or owner")
        if f["severity"]>=3 and (not f["evidence"] or f["confidence"]=="low"):
            action = "validate_evidence_before_recommendation"
        else:
            action = "prioritize" if f["severity"]>=4 else "schedule" if f["severity"]==3 else "monitor"
        volume, minutes, rate, capture = [money(f[k]) for k in ("monthly_volume","minutes_per_case","loaded_hourly_cost","realization_fraction")]
        if min(volume,minutes,rate,capture)<0 or capture>1:
            raise ValueError("Invalid benefit assumptions")
        hours = volume*minutes/Decimal(60)
        annual = (hours*rate*12*capture).quantize(Decimal(".01"))
        result.append({**f,"decision":action,"monthly_baseline_hours":str(hours.quantize(Decimal(".01"))),
                       "annual_capacity_value_scenario":str(annual),
                       "benefit_basis":"scenario, not cash savings or measured client outcome"})
    result.sort(key=lambda f:(-f["severity"], f["decision"]=="validate_evidence_before_recommendation",f["finding_id"]))
    return {"findings":result, "coverage":{d:sum(f["domain"]==d for f in result) for d in DOMAINS},
            "aggregate_benefit":"not summed; overlapping workflow benefits must be deduplicated",
            "method":"Identify, Verify, Quantify, Diagnose, Prioritize, Remediate, Validate",
            "readiness_certification":False}
