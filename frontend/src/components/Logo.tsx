import React from 'react'

interface LogoProps {
  size?: number
  className?: string
}

export default function Logo({ size = 32, className = '' }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 200"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Draught Master"
    >
      <defs>
        <filter id="logoShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="3" stdDeviation="2.5" floodColor="#000" floodOpacity="0.22" />
        </filter>
      </defs>
      <rect width="200" height="200" rx="22" fill="#EFE3CB" />
      <circle cx="128" cy="108" r="56" fill="#CFB98C" filter="url(#logoShadow)" />
      <circle cx="82" cy="92" r="56" fill="#0F0F0F" filter="url(#logoShadow)" />
    </svg>
  )
}
