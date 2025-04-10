import React from "react";

const CopyLinkButton = () => {
  const copyFormattedLink = async () => {
    const url = "https://your-domain.com/your-path";
    const buttonHtml = `
      <!--[if mso]>
      <div style="display: inline-block; mso-hide:all;">
        <a href="${url}" style="text-decoration: none;">
          <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
            xmlns:w="urn:schemas-microsoft-com:office:word"
            style="height:38px;width:120px;"
            arcsize="10%"
            strokecolor="#ff4444"
            fillcolor="#ff4444">
            <v:textbox inset="0,0,0,0">
              <center style="color:#ffffff;
                font-family:Arial,sans-serif;
                font-size:14px;
                margin-top: 9px;">
                Click Here
              </center>
            </v:textbox>
          </v:roundrect>
        </a>
      </div>
      <![endif]-->
      <!--[if !mso]><!-- -->
      <a href="${url}"
         style="
           display: inline-block;
           background-color: #ff4444;
           color: white !important;
           padding: 8px 16px;
           text-decoration: none;
           border-radius: 4px;
           font-family: Arial, sans-serif;
           font-size: 14px;
           border: 0;
           mso-hide:all;
         ">
        Click Here
      </a>
      <!--<![endif]-->
    `;

    const fullHtml = `
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
      <div style="mso-hide:all; display: inline-block;">
        ${buttonHtml}
      </div>
    `;

    // Rest of clipboard code remains the same

    // Rest of clipboard code remains same

    const plainText = url;

    try {
      // Create clipboard items with both formats
      const htmlContent = new Blob([fullHtml], { type: "text/html" });
      const textContent = new Blob([plainText], { type: "text/plain" });

      await navigator.clipboard.write([
        new ClipboardItem({
          "text/html": htmlContent,
          "text/plain": textContent,
        }),
      ]);
      alert("Copied formatted link!");
    } catch (err) {
      // Fallback for unsupported browsers
      const textArea = document.createElement("textarea");
      textArea.value = plainText;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      alert("URL copied as plain text");
    }
  };

  return (
    <button
      onClick={copyFormattedLink}
      style={{
        padding: "8px 16px",
        backgroundColor: "#007bff",
        color: "white",
        border: "none",
        borderRadius: "4px",
        cursor: "pointer",
      }}
    >
      Copy Formatted Links3
    </button>
  );
};

export default CopyLinkButton;
