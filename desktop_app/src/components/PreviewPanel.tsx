import type { TemplatePreview } from "../types/preview";

type Props = {
  preview: TemplatePreview | null;
};

function renderExcel(preview: TemplatePreview) {
  return preview.sheets.map((sheet) => (
    <section key={sheet.name} className="sheet-card">
      <h3>{sheet.name}</h3>
      <div className="table-wrap">
        <table>
          <tbody>
            {sheet.rows.length === 0 ? (
              <tr>
                <td>空工作表</td>
              </tr>
            ) : (
              sheet.rows.map((row, rowIndex) => (
                <tr key={`${sheet.name}-${rowIndex}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${sheet.name}-${rowIndex}-${cellIndex}`}>{cell}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  ));
}

function renderDocx(preview: TemplatePreview) {
  return (
    <section className="docx-card">
      <h3>文档段落</h3>
      {preview.textSections.length === 0 ? (
        <p className="placeholder">未解析出正文内容</p>
      ) : (
        preview.textSections.map((block, index) => <p key={index}>{block}</p>)
      )}
    </section>
  );
}

export function PreviewPanel({ preview }: Props) {
  if (!preview) {
    return <div className="empty-state">请选择模板文件开始预览</div>;
  }

  return (
    <div className="preview-panel">
      <div className="preview-header">
        <div>
          <h2>实时预览</h2>
          <p className="file-path">{preview.filePath}</p>
        </div>
        <div className="meta">
          <span>类型: {preview.fileType}</span>
          <span>更新时间: {new Date(preview.updatedAt).toLocaleString()}</span>
        </div>
      </div>

      {preview.warnings.length > 0 && (
        <div className="warning-box">
          {preview.warnings.map((warning, index) => (
            <p key={index}>{warning}</p>
          ))}
        </div>
      )}

      {preview.fileType === "docx" ? renderDocx(preview) : renderExcel(preview)}
    </div>
  );
}
