import React from "react";

export const Logo = ({ size = 32, withWordmark = true, dark = true }) => {
  const arrowFill = "#2CFF05";
  const main = dark ? "#FFFFFF" : "#000000";
  return (
    <div className="flex items-center gap-2" data-testid="oc-logo">
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
        <path d="M22 14 C12 14 8 22 8 32 C8 44 14 50 24 50 C30 50 34 47 36 43 L30 40 C29 42 27 44 24 44 C19 44 16 40 16 32 C16 24 19 20 24 20 C27 20 29 22 30 24 L36 21 C34 17 30 14 22 14 Z" fill={main}/>
        <path d="M40 50 L40 18 L46 18 L46 50 Z" fill={main}/>
        <rect x="49" y="10" width="3" height="9" fill={arrowFill} transform="rotate(20 50 14)"/>
        <rect x="53" y="13" width="3" height="9" fill={arrowFill} transform="rotate(20 54 17)"/>
        <rect x="57" y="16" width="3" height="9" fill={arrowFill} transform="rotate(20 58 20)"/>
      </svg>
      {withWordmark && (
        <span className="font-display font-black text-xl tracking-tight" style={{ color: main }}>
          OUT<span style={{ color: arrowFill }}>CLIPPED</span>
        </span>
      )}
    </div>
  );
};
