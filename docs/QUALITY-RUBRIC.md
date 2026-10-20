**QUY ĐỊNH MỚI CỦA CHỦ SỞ HỮU — 20/10/2026:** Ngưỡng SEO **≥76/100** và Quality **≥76/100** (trên 75), theo `config/qa-rules.json`. G3 nguồn ngoài là **tham khảo có cảnh báo để audit sau**, không chặn bài chỉ vì trích dẫn đổi câu chữ, ngày kiểm tra cũ, 404 hoặc nguồn tạm không mở được. Chưa đọc live phải ghi `live_checked=false`, ghi `source_advisories`; không gọi đó là đã xác minh. Giữ chặn nguồn URL không an toàn, nguồn pháp luật không có URL chính thức, giá/địa chỉ sai, bịa trải nghiệm, sai URL/canonical/danh mục, trùng bài, Writer receipt và G7. Các câu cũ ghi ngưỡng 85 hay bắt nguồn khớp nguyên văn đã **hết hiệu lực**. Không chỉnh điểm JSON, không bỏ gate.

# Six hard gates

1. Identity: Topic ID, title, keyword, intent, taxonomy, canonical và đường dẫn phải khớp manifest PLANNED.
2. Nội dung: 1.600–5.000 từ thực, metadata, H2, trả lời trực tiếp, không lặp đoạn/câu, placeholder, stuffing, raw HTML/script, thiếu alt.
3. Sự thật: so business facts, kiểm giá theo kỳ, phone/address, nguồn tham khảo có ghi cảnh báo audit, bằng chứng ngoại biên của writer gắn hash body. Thiếu bằng chứng pháp lý -> REVIEW. Không có AI reviewer trong Actions.
4. Collision: title/slug/canonical/intent key, text shingles với full-text inventory và các draft; evidence review của topic phải còn khớp các nội dung gần nhất.
5. Links: đúng URL đã publish trong inventory; live QA kiểm HTTP và indexability; có link cluster và lý do ngữ cảnh. Query/draft links bị chặn.
6. Publish safety: submission hash/session, mapping key và toàn bộ parent path, site allowlist, legacy protected registry, production gate và create-only ledger.

Quality ≥76 và SEO ≥70 là chỉ báo kỹ thuật. Chúng không ghi đè bất kỳ hard gate FAIL hoặc REVIEW nào. Nội dung lỗi vào REPAIR đúng ID; writer sửa rồi push lại qua cùng contract. Những đánh giá semantic/factual dựa vào nghiên cứu thật của external writer, không phải bằng chứng Google hay bảo đảm sự thật hoàn toàn từ regex.

QA evidence chứa file hash, body hash, rules hash, inventory hash, thời điểm và source evidence; file thay đổi phải QA lại. Kết quả unit test với fixture tổng hợp không phải bài SEO thật đạt QA. Báo cáo phải tách hai loại.
