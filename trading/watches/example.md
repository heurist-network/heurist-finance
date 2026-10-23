---
status: example           # set to `active` to have scripts/watch.py check it
---
Example watch. The body is the instruction for the agent: what to check, what is already
known, what counts as a finding, and which sources count.

Check whether NVIDIA has filed an 8-K with Item 2.02 (quarterly results) since the last
known one.
`uv run python scripts/hf_tool.py call sec filing_timeline query=NVDA 'forms=["8-K"]' limit=3 include_links=true`
Already known: the 8-K dated YYYY-MM-DD.
A new Item 2.02 8-K is a finding: report revenue, the next-quarter guide and the URL.
Use only sec.gov or investor.nvidia.com text.
