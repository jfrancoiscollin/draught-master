import React from 'react'
import logoSrc from '../assets/logo.png'

interface LogoProps {
  size?: number
  className?: string
}

export default function Logo({ size = 32, className = '' }: LogoProps) {
  return (
    <img
      src={logoSrc}
      alt="Draught Master"
      width={size}
      height={size}
      className={className}
      style={{ objectFit: 'contain' }}
    />
  )
}
