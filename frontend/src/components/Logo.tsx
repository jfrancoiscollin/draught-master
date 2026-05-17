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
      <circle cx="191.9" cy="229.8" r="166.1" fill="#111111" stroke="#EAE2D6" strokeWidth="3.6" />
      <path
        d="M 321.9 117.9 A 166.1 166.1 0 1 1 321.9 450.0 L 321.9 388.7 A 104.7 104.7 0 1 0 321.9 179.3 Z"
        fill="#EAE2D6"
      />
    </svg>
  )
}
