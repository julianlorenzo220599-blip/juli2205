"""Build reorganized Despiece workbook with dashboard."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

SRC = "./DESPIECE_LISTA_COMPLETA_3.xlsx"
DST = "./output/DESPIECE_KITS_DASHBOARD.xlsx"

KITS = [
    ("EC-3K",   "Economy 3 kW",                  "Monofásica", "On-Grid", 3,  6,  "N"),
    ("EC-5K",   "Economy Plus 5 kW",             "Monofásica", "On-Grid", 5,  10, "N"),
    ("EC-6K",   "Economy Pro 6 kW",              "Monofásica", "On-Grid", 6,  12, "N"),
    ("AC/R-3K", "Always Connected / Rural 3 kW", "Monofásica", "Híbrido", 3,  6,  "N"),
    ("AC/R-5K", "Always Connected / Rural 5 kW", "Monofásica", "Híbrido", 5,  12, "N"),
    ("ECT-8K",  "Economy T 8 kW",                "Trifásica",  "On-Grid", 8,  16, "N"),
    ("ECT-12K", "Economy T Plus 12 kW",          "Trifásica",  "On-Grid", 12, 24, "N"),
    ("ECT-20K", "Economy T Pro 20 kW",           "Trifásica",  "On-Grid", 20, 40, "N"),
    ("PS-8K",   "Power Station 8 kW",            "Trifásica",  "Híbrido", 8,  16, "S"),
    ("PS-10K",  "Power Station Plus 10 kW",      "Trifásica",  "Híbrido", 10, 18, "S"),
    ("PS-12K",  "Power Station Pro 12 kW",       "Trifásica",  "Híbrido", 12, 24, "S"),
    ("PS-15K",  "Power Station Mega 15 kW",      "Trifásica",  "Híbrido", 15, 32, "S"),
]

INV = {
    "EC-3K":   (1, "Inversor Monofásico ON-GRID 3 kW", "Inverters", "GOODWE", "GW3000-XS-30"),
    "EC-5K":   (1, "Inversor Monofásico ON-GRID 5 kW", "Inverters", "GOODWE", "GW5000-MS-30"),
    "EC-6K":   (1, "Inversor Monofásico ON-GRID 6 kW", "Inverters", "GOODWE", "GW6000-MS-30"),
    "AC/R-3K": (1, "Inversor Monofásico HIBRIDO 3 kW", "Inverters", "GOODWE", "GW3000-ES-20"),
    "AC/R-5K": (1, "Inversor Monofásico HIBRIDO 5 kW", "Inverters", "GOODWE", "GW5000-ES-20"),
    "ECT-8K":  (1, "Inversor Trifásico ON-GRID 8 kW",  "Inverters", "GOODWE", "GW8000-SDT-30"),
    "ECT-12K": (1, "Inversor Trifásico ON-GRID 12 kW", "Inverters", "GOODWE", "GW12K-SDT-30"),
    "ECT-20K": (1, "Inversor Trifásico ON-GRID 20 kW", "Inverters", "GOODWE", "GW20K-SDT-30"),
    "PS-8K":   (1, "Inversor Trifásico HIBRIDO 8 kW",  "Inverters", "GOODWE", "GW8000-ET-20"),
    "PS-10K":  (1, "Inversor Trifásico HIBRIDO 10 kW", "Inverters", "GOODWE", "GW10K-ET-20"),
    "PS-12K":  (1, "Inversor Trifásico HIBRIDO 12 kW", "Inverters", "GOODWE", "GW12K-ET-20"),
    "PS-15K":  (1, "Inversor Trifásico HIBRIDO 15 kW", "Inverters", "GOODWE", "GW15K-ET-20"),
}
PANEL = ("Módulo Fotovoltaico TOPCon Bifacial 585w", "Paneles FV", "TCL SOLAR", "TCL-MI585DH182-72NT")
CABLE = ("SET Cables + Conectores", "Cables", "GENERICO", "CC-20")
GMK110 = (1, "Smart Energy Controller Monofásico", "Accesorios", "GOODWE", "GMK110")
GMK330 = (1, "Smart Energy Controller Trifásico",  "Accesorios", "GOODWE", "GMK330")
BAT_LV = ("Batería 5kWh - 48V (con supresión de fuego)", "Baterías", "GOODWE", "LX U5.0-30")
BAT_HV = ("Batería Apilable 5kWh - HV", "Baterías", "GOODWE", "LX D5.0-10")

BAT = {
    "EC-3K":   (1, 0, None, GMK110),
    "EC-5K":   (2, 0, None, GMK110),
    "EC-6K":   (2, 0, None, GMK110),
    "AC/R-3K": (1, 1, "LV", GMK110),
    "AC/R-5K": (2, 1, "LV", GMK110),
    "ECT-8K":  (2, 0, None, GMK330),
    "ECT-12K": (3, 0, None, GMK330),
    "ECT-20K": (5, 0, None, GMK330),
    "PS-8K":   (2, 1, "HV", GMK330),
    "PS-10K":  (3, 1, "HV", GMK330),
    "PS-12K":  (3, 2, "HV", GMK330),
    "PS-15K":  (4, 2, "HV", GMK330),
}

ESTR = {
    "EC-3K":   (1, 6),
    "EC-5K":   (2, 5),
    "EC-6K":   (2, 6),
    "AC/R-3K": (1, 6),
    "AC/R-5K": (2, 6),
    "ECT-8K":  (2, 8),
    "ECT-12K": (4, 6),
    "ECT-20K": (5, 8),
    "PS-8K":   (2, 8),
    "PS-10K":  (3, 6),
    "PS-12K":  (4, 6),
    "PS-15K":  (4, 8),
}

SOPORTE = {"PS-8K": 1, "PS-10K": 1, "PS-12K": 2, "PS-15K": 2}

ESTR_DETALLE = {
    "C-5U": [(12, "MiniMET 0.5m Mini Riel Solarmet", "NESTMNR050"),
             (1,  "Kit Anclajes Laterales",           "NESTSKITAL"),
             (2,  "Kit Anclajes Medios - 4 Paneles",  "NESTSKITM4")],
    "C-6U": [(14, "MiniMET 0.5m Mini Riel Solarmet", "NESTMNR050"),
             (1,  "Kit Anclajes Laterales",           "NESTSKITAL"),
             (2,  "Kit Anclajes Medios - 4 Paneles",  "NESTSKITM4")],
    "C-8U": [(18, "MiniMET 0.5m Mini Riel Solarmet", "NESTMNR050"),
             (1,  "Kit Anclajes Laterales",           "NESTSKITAL"),
             (3,  "Kit Anclajes Medios - 4 Paneles",  "NESTSKITM4")],
    "T-5U": [(4, "Perfil CODA N2 (3.55m)",          "NESTSCO35D"),
             (2, "Anclaje Teja V2",                 "NESTSTEJA1"),
             (1, "Kit Anclajes Laterales",          "NESTSKITAL"),
             (2, "Kit Anclajes Medios - 4 Paneles", "NESTSKITM4"),
             (1, "Kit Conexion CODA N2",            "NESTSKITCX")],
    "T-6U": [(4, "Perfil CODA N2 (3.55m)",          "NESTSCO35D"),
             (2, "Anclaje Teja V2",                 "NESTSTEJA1"),
             (1, "Kit Anclajes Laterales",          "NESTSKITAL"),
             (2, "Kit Anclajes Medios - 4 Paneles", "NESTSKITM4"),
             (1, "Kit Conexion CODA N2",            "NESTSKITCX")],
    "T-8U": [(6, "Perfil CODA N2 (3.55m)",          "NESTSCO35D"),
             (2, "Anclaje Teja V2",                 "NESTSTEJA1"),
             (1, "Kit Anclajes Laterales",          "NESTSKITAL"),
             (3, "Kit Anclajes Medios - 4 Paneles", "NESTSKITM4"),
             (2, "Kit Conexion CODA N2",            "NESTSKITCX")],
    "SL-5U": [(3, "Perfil CODA N2 (4.75m) V2",       "IESTSCO47D"),
              (1, "Kit Anclajes Laterales",          "NESTSKITAL"),
              (2, "Kit Anclajes Medios - 4 Paneles", "NESTSKITM4"),
              (1, "Kit Conexion CODA N2",            "NESTSKITCX"),
              (5, "Triangulo Aluminio Regulable",    "NESTSTRIAN")],
    "SL-6U": [(3, "Perfil CODA N2 (4.75m) V2",       "IESTSCO47D"),
              (1, "Kit Anclajes Laterales",          "NESTSKITAL"),
              (2, "Kit Anclajes Medios - 4 Paneles", "NESTSKITM4"),
              (1, "Kit Conexion CODA N2",            "NESTSKITCX"),
              (6, "Triangulo Aluminio Regulable",    "NESTSTRIAN")],
    "SL-8U": [(4, "Perfil CODA N2 (4.75m) V2",       "IESTSCO47D"),
              (1, "Kit Anclajes Laterales",          "NESTSKITAL"),
              (3, "Kit Anclajes Medios - 4 Paneles", "NESTSKITM4"),
              (1, "Kit Conexion CODA N2",            "NESTSKITCX"),
              (7, "Triangulo Aluminio Regulable",    "NESTSTRIAN")],
}

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HDR_FILL = PatternFill("solid", fgColor="1F4E78")
HDR_FONT = Font(bold=True, color="FFFFFF", size=11)
SUB_FILL = PatternFill("solid", fgColor="D9E1F2")
SUB_FONT = Font(bold=True, color="1F3864")
TITLE_FONT = Font(bold=True, size=16, color="1F4E78")
LABEL_FONT = Font(bold=True, size=11, color="1F4E78")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
INPUT_FONT = Font(bold=True, size=12)
CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def style_header(ws, row, cols):
    for c in cols:
        cell = ws.cell(row=row, column=c)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = CENTER
        cell.border = BORDER


def autosize(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


import os
os.makedirs(os.path.dirname(DST), exist_ok=True)

wb = openpyxl.Workbook()

ws_k = wb.active
ws_k.title = "Kits"
headers = ["Código Kit", "Nombre", "Fase", "Tipo", "Potencia (kW)", "Cant. Paneles", "Lleva Soporte Batería"]
ws_k.append(headers)
style_header(ws_k, 1, range(1, len(headers) + 1))
for k in KITS:
    ws_k.append(list(k))
for r in range(2, len(KITS) + 2):
    for c in range(1, len(headers) + 1):
        ws_k.cell(row=r, column=c).border = BORDER
        ws_k.cell(row=r, column=c).alignment = CENTER if c != 2 else LEFT
autosize(ws_k, [12, 32, 14, 12, 14, 14, 22])
ws_k.freeze_panes = "A2"

ws_b = wb.create_sheet("BOM_Base")
hdr = ["Código Kit", "Tipo", "Qty", "Item", "Categoría", "Marca", "Código"]
ws_b.append(hdr)
style_header(ws_b, 1, range(1, len(hdr) + 1))
for codigo, nombre, fase, tipo, kw, paneles, sop in KITS:
    inv_qty, inv_item, inv_cat, inv_mk, inv_cod = INV[codigo]
    qcab, qbat, tbat, smart = BAT[codigo]
    ws_b.append([codigo, "Base", inv_qty, inv_item, inv_cat, inv_mk, inv_cod])
    ws_b.append([codigo, "Base", paneles, *PANEL])
    ws_b.append([codigo, "Base", qcab, *CABLE])
    if qbat > 0:
        bat = BAT_LV if tbat == "LV" else BAT_HV
        ws_b.append([codigo, "Base", qbat, *bat])
    s_q, s_it, s_cat, s_mk, s_cod = smart
    ws_b.append([codigo, "Base", s_q, s_it, s_cat, s_mk, s_cod])
for r in range(2, ws_b.max_row + 1):
    for c in range(1, len(hdr) + 1):
        ws_b.cell(row=r, column=c).border = BORDER
        ws_b.cell(row=r, column=c).alignment = LEFT if c == 4 else CENTER
autosize(ws_b, [12, 10, 8, 42, 14, 12, 22])
ws_b.freeze_panes = "A2"

ws_e = wb.create_sheet("BOM_Estructura")
hdr_e = ["Código Kit", "Tipo Estructura", "Qty", "Item", "Categoría", "Marca", "Código"]
ws_e.append(hdr_e)
style_header(ws_e, 1, range(1, len(hdr_e) + 1))
TIPOS = [("Chapa", "C"), ("Teja", "T"), ("Suelo/Losa", "SL")]
for k in KITS:
    codigo = k[0]
    qty, size = ESTR[codigo]
    for nombre_tipo, prefix in TIPOS:
        set_code = f"{prefix}-{size}U"
        if prefix == "SL":
            item = f"Set Estructuras Suelo / Losa (x{size})"
        else:
            item = f"Set Estructuras Techo Coplanar {nombre_tipo} (x{size})"
        ws_e.append([codigo, nombre_tipo, qty, item, "Estructuras", "SOLARMET", set_code])
for r in range(2, ws_e.max_row + 1):
    for c in range(1, len(hdr_e) + 1):
        ws_e.cell(row=r, column=c).border = BORDER
        ws_e.cell(row=r, column=c).alignment = LEFT if c == 4 else CENTER
autosize(ws_e, [12, 14, 8, 42, 14, 12, 12])
ws_e.freeze_panes = "A2"

ws_s = wb.create_sheet("BOM_Soporte")
hdr_s = ["Código Kit", "Tipo Soporte", "Qty", "Item", "Categoría", "Marca", "Código"]
ws_s.append(hdr_s)
style_header(ws_s, 1, range(1, len(hdr_s) + 1))
for codigo, qty in SOPORTE.items():
    ws_s.append([codigo, "Pared", qty, "Soporte batería Lynx D para pared", "Accesorios", "SOLARMET", "Hanger assembly for Lynx D"])
    ws_s.append([codigo, "Suelo", qty, "Base batería Lynx D para suelo",   "Accesorios", "SOLARMET", "Base assembly for Lynx D"])
for r in range(2, ws_s.max_row + 1):
    for c in range(1, len(hdr_s) + 1):
        ws_s.cell(row=r, column=c).border = BORDER
        ws_s.cell(row=r, column=c).alignment = LEFT if c == 4 else CENTER
autosize(ws_s, [12, 14, 8, 42, 14, 12, 28])
ws_s.freeze_panes = "A2"

ws_ed = wb.create_sheet("Estructuras_Detalle")
hdr_ed = ["Código Set", "Qty (por set)", "Item", "Categoría", "Marca", "Código"]
ws_ed.append(hdr_ed)
style_header(ws_ed, 1, range(1, len(hdr_ed) + 1))
for set_code, comps in ESTR_DETALLE.items():
    for q, it, cod in comps:
        ws_ed.append([set_code, q, it, "Estructuras", "SOLARMET", cod])
for r in range(2, ws_ed.max_row + 1):
    for c in range(1, len(hdr_ed) + 1):
        ws_ed.cell(row=r, column=c).border = BORDER
        ws_ed.cell(row=r, column=c).alignment = LEFT if c == 3 else CENTER
autosize(ws_ed, [12, 14, 36, 14, 12, 14])
ws_ed.freeze_panes = "A2"

ws_md = wb.create_sheet("Master_Data")
if os.path.exists(SRC):
    src = openpyxl.load_workbook(SRC, data_only=True)
    if "Listado Master DATA" in src.sheetnames:
        src_md = src["Listado Master DATA"]
        for row in src_md.iter_rows(values_only=True):
            ws_md.append(row)
        style_header(ws_md, 1, range(1, src_md.max_column + 1))
        for r in range(2, ws_md.max_row + 1):
            for c in range(1, src_md.max_column + 1):
                ws_md.cell(row=r, column=c).border = BORDER
                ws_md.cell(row=r, column=c).alignment = LEFT if c == 4 else CENTER
        autosize(ws_md, [14, 14, 28, 46])
else:
    ws_md.append(["Categoría", "Marca", "Código (SKU)", "Descripción"])
    style_header(ws_md, 1, range(1, 5))
ws_md.freeze_panes = "A2"

ws_d = wb.create_sheet("Dashboard", 0)
ws_d["B2"] = "DESPIECE DE KITS — Dashboard"
ws_d["B2"].font = TITLE_FONT
ws_d.merge_cells("B2:G2")
ws_d["B2"].alignment = Alignment(horizontal="left", vertical="center")

ws_d["B4"] = "Kit:"
ws_d["B5"] = "Estructura:"
ws_d["B6"] = "Soporte Batería:"
for c in ["B4", "B5", "B6"]:
    ws_d[c].font = LABEL_FONT
    ws_d[c].alignment = Alignment(horizontal="right", vertical="center")

ws_d["C4"] = "EC-3K"
ws_d["C5"] = "Chapa"
ws_d["C6"] = "Pared"
for c in ["C4", "C5", "C6"]:
    ws_d[c].fill = INPUT_FILL
    ws_d[c].font = INPUT_FONT
    ws_d[c].alignment = CENTER
    ws_d[c].border = BORDER

ws_d["E4"] = "Nombre:"
ws_d["F4"] = '=IFERROR(XLOOKUP(C4,Kits!A:A,Kits!B:B),"")'
ws_d["E5"] = "Fase / Tipo:"
ws_d["F5"] = '=IFERROR(XLOOKUP(C4,Kits!A:A,Kits!C:C)&" / "&XLOOKUP(C4,Kits!A:A,Kits!D:D),"")'
ws_d["E6"] = "Potencia / Paneles:"
ws_d["F6"] = '=IFERROR(XLOOKUP(C4,Kits!A:A,Kits!E:E)&" kW · "&XLOOKUP(C4,Kits!A:A,Kits!F:F)&" paneles","")'
for c in ["E4", "E5", "E6"]:
    ws_d[c].font = LABEL_FONT
    ws_d[c].alignment = Alignment(horizontal="right", vertical="center")
for c in ["F4", "F5", "F6"]:
    ws_d[c].alignment = LEFT
    ws_d[c].border = BORDER

dv_kit = DataValidation(type="list", formula1=f"=Kits!$A$2:$A${len(KITS) + 1}", allow_blank=False)
dv_kit.add("C4")
ws_d.add_data_validation(dv_kit)
dv_est = DataValidation(type="list", formula1='"Chapa,Teja,Suelo/Losa"', allow_blank=False)
dv_est.add("C5")
ws_d.add_data_validation(dv_est)
dv_sop = DataValidation(type="list", formula1='"Pared,Suelo,N/A"', allow_blank=True)
dv_sop.add("C6")
ws_d.add_data_validation(dv_sop)

row = 9
ws_d.cell(row=row, column=2, value="COMPONENTES BASE DEL KIT").font = Font(bold=True, size=12, color="FFFFFF")
ws_d.cell(row=row, column=2).fill = HDR_FILL
ws_d.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
ws_d.cell(row=row, column=2).alignment = Alignment(horizontal="left", vertical="center", indent=1)
row += 1
sub_hdr = ["Qty", "Item", "Categoría", "Marca", "Código"]
for i, h in enumerate(sub_hdr, 2):
    cell = ws_d.cell(row=row, column=i, value=h)
    cell.fill = SUB_FILL
    cell.font = SUB_FONT
    cell.alignment = CENTER
    cell.border = BORDER
row += 1
ws_d.cell(row=row, column=2, value='=FILTER(BOM_Base!C:G, BOM_Base!A:A=C4, "")')
for rr in range(row, row + 12):
    for cc in range(2, 7):
        c = ws_d.cell(row=rr, column=cc)
        c.border = BORDER
        c.alignment = LEFT if cc == 3 else CENTER

row = row + 13
ws_d.cell(row=row, column=2, value="ESTRUCTURA SELECCIONADA (SET)").font = Font(bold=True, size=12, color="FFFFFF")
ws_d.cell(row=row, column=2).fill = HDR_FILL
ws_d.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
ws_d.cell(row=row, column=2).alignment = Alignment(horizontal="left", vertical="center", indent=1)
row += 1
for i, h in enumerate(sub_hdr, 2):
    cell = ws_d.cell(row=row, column=i, value=h)
    cell.fill = SUB_FILL
    cell.font = SUB_FONT
    cell.alignment = CENTER
    cell.border = BORDER
row += 1
ws_d.cell(row=row, column=2, value='=FILTER(BOM_Estructura!C:G, (BOM_Estructura!A:A=C4)*(BOM_Estructura!B:B=C5), "")')
for rr in range(row, row + 3):
    for cc in range(2, 7):
        c = ws_d.cell(row=rr, column=cc)
        c.border = BORDER
        c.alignment = LEFT if cc == 3 else CENTER

row = row + 3
ws_d.cell(row=row, column=2, value="DESPIECE INTERNO DE LA ESTRUCTURA (por set)").font = Font(bold=True, size=12, color="FFFFFF")
ws_d.cell(row=row, column=2).fill = HDR_FILL
ws_d.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
ws_d.cell(row=row, column=2).alignment = Alignment(horizontal="left", vertical="center", indent=1)
row += 1
sub_hdr2 = ["Qty x set", "Qty Total", "Item", "Categoría", "Marca", "Código"]
for i, h in enumerate(sub_hdr2, 2):
    cell = ws_d.cell(row=row, column=i, value=h)
    cell.fill = SUB_FILL
    cell.font = SUB_FONT
    cell.alignment = CENTER
    cell.border = BORDER
row += 1
ws_d.cell(row=row - 2, column=8, value="Set:").font = LABEL_FONT
ws_d.cell(row=row - 2, column=9, value='=IFERROR(INDEX(BOM_Estructura!G:G, MATCH(1,(BOM_Estructura!A:A=C4)*(BOM_Estructura!B:B=C5),0)),"")').font = Font(bold=True)
ws_d.cell(row=row - 2, column=10, value="Sets:").font = LABEL_FONT
ws_d.cell(row=row - 2, column=11, value='=IFERROR(INDEX(BOM_Estructura!C:C, MATCH(1,(BOM_Estructura!A:A=C4)*(BOM_Estructura!B:B=C5),0)),0)').font = Font(bold=True)
ws_d.cell(row=row, column=2, value='=IFERROR(FILTER(Estructuras_Detalle!B:B, Estructuras_Detalle!A:A=I' + str(row - 2) + ', ""),"")')
ws_d.cell(row=row, column=3, value='=IFERROR(FILTER(Estructuras_Detalle!B:B, Estructuras_Detalle!A:A=I' + str(row - 2) + ', "")*K' + str(row - 2) + ',"")')
ws_d.cell(row=row, column=4, value='=IFERROR(FILTER(Estructuras_Detalle!C:F, Estructuras_Detalle!A:A=I' + str(row - 2) + ', ""),"")')
for rr in range(row, row + 8):
    for cc in range(2, 8):
        c = ws_d.cell(row=rr, column=cc)
        c.border = BORDER
        c.alignment = LEFT if cc == 4 else CENTER

row = row + 9
ws_d.cell(row=row, column=2, value="SOPORTE BATERÍA (solo kits HV)").font = Font(bold=True, size=12, color="FFFFFF")
ws_d.cell(row=row, column=2).fill = HDR_FILL
ws_d.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
ws_d.cell(row=row, column=2).alignment = Alignment(horizontal="left", vertical="center", indent=1)
row += 1
for i, h in enumerate(sub_hdr, 2):
    cell = ws_d.cell(row=row, column=i, value=h)
    cell.fill = SUB_FILL
    cell.font = SUB_FONT
    cell.alignment = CENTER
    cell.border = BORDER
row += 1
ws_d.cell(row=row, column=2, value='=IFERROR(FILTER(BOM_Soporte!C:G,(BOM_Soporte!A:A=C4)*(BOM_Soporte!B:B=C6),"N/A para este kit"),"N/A para este kit")')
for rr in range(row, row + 2):
    for cc in range(2, 7):
        c = ws_d.cell(row=rr, column=cc)
        c.border = BORDER
        c.alignment = LEFT if cc == 3 else CENTER

autosize(ws_d, [2, 12, 42, 14, 14, 14, 22, 6, 12, 6, 8])
ws_d.sheet_view.showGridLines = False
ws_d.row_dimensions[2].height = 26

wb.save(DST)
print("Saved:", DST)