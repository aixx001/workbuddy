"""Quick verify caller — prints full JSON results."""
import httpx
import json
import pathlib

r = httpx.post("http://localhost:8100/demo/deepeval/evaluation/verify", timeout=600)
d = r.json()

for c in d["cases"]:
    scores = {k: v for k, v in c["scores"].items()}
    print(f'{c["label"]}:  {json.dumps(scores, ensure_ascii=False)}  passed={c["passed"]}')

print(f'\nall_passed={d["all_passed"]}  total={d["total_elapsed"]}s')

# Save full result
pathlib.Path("verify_result.json").write_text(
    json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("Saved verify_result.json")
