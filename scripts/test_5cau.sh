#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONIOENCODING=utf-8
Q=(
  "Mức thuế hộ kinh doanh năm 2026"
  "thủ tục đăng ký khai sinh cho trẻ mới sinh"
  "mức phạt vượt đèn đỏ"
  "vợ tôi là tổ phó tổ tiếng anh trong trường trung học phổ thông, thì có được xếp vào nhóm viên chức quản lý hay không"
  "Nghị định 141/2026/NĐ-CP"
)
for q in "${Q[@]}"; do
  echo "########## $q"
  python3 -m legal_search.search "$q" --rerank --k 3 2>&1 | grep -E '^#[0-9]|rerank=' | sed 's/text_match=[0-9]*//'
  echo
done
