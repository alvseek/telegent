"""telegent — the Telegram bridge. A-Boxed Level 1 application package.

A thin, stateless pipe between Telegram and universal-chat-agent (the brain).
All intelligence + memory live in the brain; this repo only translates Telegram
<-> the brain's HTTP contract. Layers it doesn't need (data_*, business_*) are
present as placeholders for L1 structural consistency (see their READMEs).
"""
