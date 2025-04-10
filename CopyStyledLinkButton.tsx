// App.tsx
import React from "react";

const CopyStyledLinkButton: React.FC = () => {
  const copyStyledLink = () => {
    const html = `
      <a href="https://example.com" style="
        display: inline-block;
        padding: 8px 16px;
        background-color: #0078D4;
        color: white;
        text-decoration: none;
        border-radius: 6px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
      ">Click Me</a>`;

    const container = document.createElement("div");
    container.innerHTML = html;
    container.style.position = "fixed"; // Prevent scrolling
    container.style.opacity = "0";
    container.contentEditable = "true";
    document.body.appendChild(container);

    const range = document.createRange();
    range.selectNodeContents(container);

    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);

    try {
      const success = document.execCommand("copy");
      if (success) {
        alert("Styled link copied! Paste into Outlook!");
      } else {
        console.error("Copy command was unsuccessful");
      }
    } catch (err) {
      console.error("Copy failed", err);
    }

    selection?.removeAllRanges();
    document.body.removeChild(container);
  };

  const appStyle: React.CSSProperties = {
    textAlign: "center",
    marginTop: "100px",
    fontFamily: "Segoe UI, sans-serif",
  };

  const buttonStyle: React.CSSProperties = {
    padding: "10px 20px",
    backgroundColor: "#0078D4",
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "14px",
    cursor: "pointer",
  };

  return (
    <div style={appStyle}>
      <h2>Copy Link as Styled Button</h2>
      <button onClick={copyStyledLink} style={buttonStyle}>
        Copy Link as Button
      </button>
    </div>
  );
};

export default CopyStyledLinkButton;
