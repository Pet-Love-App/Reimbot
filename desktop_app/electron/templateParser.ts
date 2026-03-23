import fs from "node:fs";
import path from "node:path";

import mammoth from "mammoth";
import * as XLSX from "xlsx";

export type SheetPreview = {
  name: string;
  rows: string[][];
};

export type TemplatePreview = {
  filePath: string;
  fileType: "xlsx" | "xls" | "docx" | "unknown";
  updatedAt: string;
  textSections: string[];
  sheets: SheetPreview[];
  warnings: string[];
};

function extToType(filePath: string): TemplatePreview["fileType"] {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".xlsx") {
    return "xlsx";
  }
  if (ext === ".xls") {
    return "xls";
  }
  if (ext === ".docx") {
    return "docx";
  }
  return "unknown";
}

function readExcel(filePath: string): SheetPreview[] {
  const workbook = XLSX.readFile(filePath, { cellDates: true });
  return workbook.SheetNames.map((sheetName) => {
    const worksheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json<(string | number | null)[]>(worksheet, {
      header: 1,
      blankrows: false,
      raw: false,
    });

    const normalizedRows = rows
      .slice(0, 200)
      .map((row) => row.map((cell) => (cell === null || cell === undefined ? "" : String(cell))));

    return {
      name: sheetName,
      rows: normalizedRows,
    };
  });
}

async function readDocx(filePath: string): Promise<string[]> {
  const result = await mammoth.extractRawText({ path: filePath });
  const textBlocks = result.value
    .split(/\r?\n\r?\n/g)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 200);
  return textBlocks;
}

export async function parseTemplate(filePath: string): Promise<TemplatePreview> {
  const fileType = extToType(filePath);
  const stat = fs.statSync(filePath);
  const warnings: string[] = [];

  const base: TemplatePreview = {
    filePath,
    fileType,
    updatedAt: stat.mtime.toISOString(),
    textSections: [],
    sheets: [],
    warnings,
  };

  if (fileType === "xlsx" || fileType === "xls") {
    base.sheets = readExcel(filePath);
    return base;
  }

  if (fileType === "docx") {
    base.textSections = await readDocx(filePath);
    return base;
  }

  warnings.push("当前仅支持 xlsx/xls/docx 模板预览。");
  return base;
}
