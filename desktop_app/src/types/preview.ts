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
