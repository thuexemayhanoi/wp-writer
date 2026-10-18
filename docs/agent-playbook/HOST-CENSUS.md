# Runner-readable host census (shared by all agents; append your own probe results at the bottom)

**Historical diagnostic snapshot only, not an allowlist or eligibility gate.** Current source policy is [WRITER-RESEARCH-CONTRACT.md](../WRITER-RESEARCH-CONTRACT.md): any relevant verified public HTTPS source may be used; one original source can suffice for a narrow scope, with corroboration where needed. Results below were measured on one runner/date and may change.
Probe = GitHub Actions runner, QA user agent `NguyenTu-WPWriter/1.0`, 20 s timeout, TLS verified, cross-origin redirects refused. Root-page probe of 2026-10-17 13:51 UTC (workflow run 39038265480).

READABLE (HTTP 200): www.honda.com.vn, yamaha-motor.com.vn, vietnam.travel, vietnamtourism.gov.vn (root is JS-only: probe deep pages), vbpl.vn (root tiny: probe deep pages), vanban.chinhphu.vn, mps.gov.vn, mae.gov.vn, vea.mae.gov.vn, sonnmt.hanoi.gov.vn, mst.gov.vn, vov.gov.vn, chinhphu.vn, baochinhphu.vn, suckhoedoisong.vn, vnexpress.net, thanhnien.vn
NOT READABLE: vinfastauto.com (403), vme.org.vn (403), moj.gov.vn (403), csgt.vn (timeout), hanoi.gov.vn (timeout), mt.gov.vn (SSL certificate error), sogtvt.hanoi.gov.vn (timeout), sdl.hanoi.gov.vn (DNS), dulich.hanoi.gov.vn (DNS), moh.gov.vn (timeout), vr.org.vn (DNS), nchmf.gov.vn (cross-origin redirect), baogiaothong.vn (cross-origin redirect); earlier probes: tcvn.gov.vn, csgt.bocongan.gov.vn, cem.gov.vn, airhanoi.hanoi.gov.vn (timeouts/blocks), cdn.honda.com.vn PDF (PDF cannot be cited)

Previously allowlisted and runner-readable (historical labels, no current eligibility implication): honda.com.vn, yamaha-motor.com.vn, vietnam.travel, vietnamtourism.gov.vn, mae.gov.vn, vea.mae.gov.vn, sonnmt.hanoi.gov.vn, mst.gov.vn, vov.gov.vn, mps.gov.vn, vanban.chinhphu.vn, vbpl.vn.
Other readable hosts from that probe (also usable as primary article sources when appropriate and verified): chinhphu.vn, baochinhphu.vn, suckhoedoisong.vn, vnexpress.net, thanhnien.vn.

A host-level OK does not prove a deep page works. Optional exact-URL probes can help diagnose failures; do not require a separate probe before every topic. Article QA still applies the live/snapshot verification rules in the shared contract.

## Probe log (append: date | host or URL | OK/FAIL | note)
