import pandas as pd

from infuse.analysis.summary import summarize


def test_summary_from_records():
    rows = []
    for m, asr in (("A", 1), ("B", 0)):
        for i in range(12):
            rows.append({"model": m, "asr_l": asr if i % 2 else 0, "asr_h": asr, "rr": 0, "utility_l": 1, "defense": "none"})
    rows.append({"model": "A", "asr_l": 1, "asr_h": 1, "rr": 1, "utility_l": 0, "defense": "progent"})  # excluded
    t = summarize(pd.DataFrame(rows))
    assert list(t.columns) == ["LLM", "ASR-L", "ASR-H", "RR", "Utility-L", "n"]
    assert t.iloc[0]["LLM"] == "A" and abs(t.iloc[0]["ASR-L"] - 0.5) < 1e-9 and t.iloc[0]["n"] == 12
    assert t.iloc[1]["ASR-L"] == 0
