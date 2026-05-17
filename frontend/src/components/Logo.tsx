import React from 'react'

interface LogoProps {
  size?: number
  className?: string
}

export default function Logo({ size = 32, className = '' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Draught Master"
    >
      <rect width="512" height="512" fill="#F4EFE7" />
      <ellipse cx="220" cy="220" rx="92" ry="92" fill="#00000010" />
      <ellipse cx="292" cy="250" rx="92" ry="92" fill="#00000010" />
      <circle cx="220" cy="220" r="92" fill="#111111" />
      <circle cx="270" cy="250" r="58" fill="#F4EFE7" />
      <path
        d="M292 158 A92 92 0 1 1 292 342 L292 308 A58 58 0 1 0 292 192 Z"
        fill="#EAE2D6"
      />
      <text
        x="256"
        y="430"
        textAnchor="middle"
        fontFamily="Arial, Helvetica, sans-serif"
        fontSize="26"
        letterSpacing="10"
        fill="#111111"
      >
        DRAUGHT
      </text>
      <text
        x="256"
        y="470"
        textAnchor="middle"
        fontFamily="Arial, Helvetica, sans-serif"
        fontSize="26"
        letterSpacing="10"
        fill="#111111"
      >
        MASTER
      </text>
    </svg>
  )
}
