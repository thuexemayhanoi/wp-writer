#!/usr/bin/env python3
"""Generate standard Office Open XML .xlsx files from approved CSV planning rows.

Produces only static reviewable spreadsheet views. plan.json + status.json are
authoritative. Does not invoke WordPress, claim writer slots or bypass QA.
"""
import csv
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'editorial'/'title-plan-1482'
MAIN='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
ET.register_namespace('',MAIN)
ET.register_namespace('r',REL)
ET.register_namespace('p',PKG)
ET.register_namespace('ct',CT)

def el(parent,tag,attributes=None,value=None):
    child=ET.SubElement(parent,'{'+MAIN+'}'+tag,attributes or {})
    if value is not None:child.text=str(value)
    return child

def col_letter(n):
    s=''
    while n:
        n,v=divmod(n-1,26)
        s=chr(65+v)+s
    return s

def worksheet_xml(rows,widths,header=True,filter_range=None):
    root=ET.Element('{'+MAIN+'}worksheet')
    views=el(root,'sheetViews')
    view=el(views,'sheetView',{'workbookViewId':'0'})
    if header:el(view,'pane',{'ySplit':'1','topLeftCell':'A2','activePane':'bottomLeft','state':'frozen'})
    cols=el(root,'cols')
    for i,w in enumerate(widths,1):
        el(cols,'col',{'min':str(i),'max':str(i),'width':str(w),'customWidth':'1'})
    data=el(root,'sheetData')
    for ri,row in enumerate(rows,1):
        r=el(data,'row',{'r':str(ri),'ht':str(32 if ri==1 else 23),'customHeight':'1'})
        for ci,value in enumerate(row,1):
            if value is None or value=='':continue
            pos=f'{col_letter(ci)}{ri}'
            style='1' if ri==1 else ('2' if ri%2==1 else '0')
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                cell=el(r,'c',{'r':pos,'s':style,'t':'n'})
                el(cell,'v',value=str(value))
            else:
                if str(value)=='PUBLISHED_G7_PASS':style='3'
                cell=el(r,'c',{'r':pos,'s':style,'t':'inlineStr'})
                is_=el(cell,'is')
                el(is_,'t',{'{http://www.w3.org/XML/1998/namespace}space':'preserve'},str(value))
    if filter_range:el(root,'autoFilter',{'ref':filter_range})
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def plain_xml(s):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'+s).encode('utf-8')

def styles_xml():
    # 0 normal; 1 brand header; 2 alternating; 3 verified success.
    return plain_xml('''<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
      <fonts count="2"><font><sz val="10"/><name val="Aptos"/></font>
      <font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Aptos"/></font></fonts>
      <fills count="4"><fill><patternFill patternType="none"/></fill>
      <fill><patternFill patternType="gray125"/></fill>
      <fill><patternFill patternType="solid"><fgColor rgb="FF164E63"/><bgColor indexed="64"/></patternFill></fill>
      <fill><patternFill patternType="solid"><fgColor rgb="FFF0F6FA"/><bgColor indexed="64"/></patternFill></fill></fills>
      <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
      <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
      <cellXfs count="4">
      <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
      <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1"/>
      <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/>
      <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/></cellXfs>
      <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
      </styleSheet>''')

def workbook_xml():
    return plain_xml('''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets><sheet name="Tieu de" sheetId="1" r:id="rId1"/>
    <sheet name="Tong quan" sheetId="2" r:id="rId2"/>
    <sheet name="Huong dan" sheetId="3" r:id="rId3"/></sheets></workbook>''')

def workbook_rels():
    return plain_xml('''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
    <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
    </Relationships>''')

def content_types():
    return plain_xml('''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
    <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
    <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
    </Types>''')

def zip_build(filepath,sheets):
    files={'[Content_Types].xml':content_types(),
           '_rels/.rels':plain_xml('''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
           <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
           Target="xl/workbook.xml"/></Relationships>'''),
           'xl/workbook.xml':workbook_xml(),
           'xl/_rels/workbook.xml.rels':workbook_rels(),
           'xl/styles.xml':styles_xml()}
    for i,xml in enumerate(sheets,1):files[f'xl/worksheets/sheet{i}.xml']=xml
    with zipfile.ZipFile(filepath,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zf:
        for name,content in files.items():
            info=zipfile.ZipInfo(name)
            info.date_time=(2026,10,20,0,0,0)
            info.compress_type=zipfile.ZIP_DEFLATED
            zf.writestr(info,content)
    with zipfile.ZipFile(filepath,'r') as zf:
        bad=zf.testzip()
        if bad:raise ValueError('Corrupt OOXML member '+bad)
        for name in files:
            ET.fromstring(zf.read(name))

def main():
    plan=json.loads((BASE/'plan.json').read_text(encoding='utf-8'))
    ids=set(x['plan_id'] for x in plan['rows'])
    if len(ids)!=1482:raise ValueError('Invalid title index')
    count=0
    for part in range(1,4):
        csvpath=BASE/f'seo-tieu-de-{part:02d}-494.csv'
        with csvpath.open('r',encoding='utf-8-sig',newline='') as fh:
            rd=csv.reader(fh);rows=list(rd)
        if len(rows)!=495 or len(rows[0])!=18:raise ValueError('Invalid sheet dimensions')
        actual=rows[1:]
        if any(len(row)!=18 for row in actual):raise ValueError('Malformed row')
        if any(not 60<=len(row[1])<=80 for row in actual):
            raise ValueError('Title outside 60-80 characters')
        if any(int(row[5]) not in (163,164,165,166,167,168,160,169,170,161,171,172,173,174,175,176,177,156)
               for row in actual):raise ValueError('Unknown category')
        count+=len(actual)
        counts=Counter(row[12] for row in actual)
        overview=[
            ['KẾ HOẠCH TIÊU ĐỀ SEO - TẬP '+str(part),'Giá trị'],
            ['Số tiêu đề',len(actual)],
            ['Danh mục con hiện có',18],
            ['Đã xuất bản qua G7',counts.get('PUBLISHED_G7_PASS',0)],
            ['Còn ở bước lập kế hoạch',counts.get('PLANNED',0)],
            ['Tổng danh mục của ba tập',1482],
            ['Số bài cũ đã đối chiếu',518]
        ]
        guide=[
            ['QUY TẮC','HƯỚNG DẪN'],
            ['Nguồn sự thật','plan.json là hàng đợi; bảng Excel được tạo lại sau cập nhật G7'],
            ['SEO','Không sản sinh thêm tiêu đề có cụm Thuê xe máy Hà Nội'],
            ['Danh mục','Dùng Term ID cha con có thật; không tạo chuyên mục mới'],
            ['51 phường','Giữ riêng chiến dịch 51 phường (Term 182) để không trùng'],
            ['Nghiên cứu','Tìm và đối chiếu 1-4 trang nguồn cho mỗi tiêu đề'],
            ['Luật','Bất kỳ khẳng định pháp luật nào đều cần nguồn chính thức'],
            ['QA','Writer và Publisher giữ QA >=85; không thay đổi các cổng'],
            ['Đã đăng','Chỉ xác nhận khi ledger có phase VERIFIED và G7 PASS'],
            ['Cũ','Trước mỗi bài phải rà soát WP và kho chủ đề để chống trùng']
        ]
        sheets=[
            worksheet_xml(rows,[14,60,12,18,31,11,12,24,37,59,12,12,24,17,14,51,16,22],
                          filter_range='A1:R495'),
            worksheet_xml(overview,[48,22],filter_range=None),
            worksheet_xml(guide,[24,93],filter_range=None)
        ]
        file=BASE/f'seo-tieu-de-{part:02d}-494.xlsx'
        zip_build(file,sheets)
        if file.stat().st_size<15000:raise ValueError('Workbook unexpectedly small')
        print(str(file),file.stat().st_size)
    if count!=1482:raise ValueError('Not exactly 1482 titles')

if __name__=='__main__':main()
