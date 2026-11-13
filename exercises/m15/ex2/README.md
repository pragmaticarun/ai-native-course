# Ex 15.2: a prompt-injection fixture and a guard that catches it

Screen content is untrusted: web pages, emails and *notifications* can carry instructions aimed at
your agent. Write:

1. `NOTIFICATION`: a realistic Android notification (string) that tries to make a mobile agent tap
   "Delete all" by telling it to ignore its previous instructions. The tests check that your own
   guard flags it.
2. `normalise(text)`: lower-case; remove zero-width characters (U+200B, U+200C, U+200D, U+2060,
   U+FEFF); map the Cyrillic lookalikes `а е о р с і` to `a e o p c i`; collapse whitespace.
3. `scan(text)`: after `normalise`, return the sorted list of matched rule names from:
   `override` ("ignore/disregard/forget ... previous/prior/above/earlier instructions"),
   `role` ("you are now ..." / "new instructions:" / "system prompt"),
   `exfil` (an email address *together with* forward/send/share in the same text),
   `urgency_action` ("immediately|urgent|now" together with "tap|click|delete|transfer").
4. `allow(action, target, screen_text)`: block (return False) any `tap`/`click` whose target matches
   delete/forward/send/pay/transfer **if** the current screen scan is non-empty; otherwise True.

The M15 worked example's `Guard` has a simpler version; this one survives cheap obfuscation.
Heuristics are a tripwire, not a defence on their own: keep the confirmation step for consequential
actions regardless.
