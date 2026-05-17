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
      <rect width="512" height="512" fill="#1A1A1A" />
      <circle cx="220" cy="220" r="92" fill="#111111" stroke="#EAE2D6" strokeWidth="2" />
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
        fill="#EAE2D6"
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
        fill="#EAE2D6"
      >
        MASTER
      </text>
    </svg>
  )
}
