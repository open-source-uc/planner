import React, { useEffect, useState } from 'react'
import JSConfetti from 'js-confetti'

// Confetti context to pass the confetti instance to the components
export const ConfettiContext = React.createContext<JSConfetti | null>(null)

// Confetti provider to initialize the confetti instance
export function ConfettiProvider ({ children }: { children: React.ReactNode }): JSX.Element {
  const [confetti, setConfetti] = useState<JSConfetti | null>(null)

  useEffect(() => {
    const confettiInstance = new JSConfetti()
    setConfetti(confettiInstance)
  }, [])

  return (
        <ConfettiContext.Provider value={confetti}>
        {children}
        </ConfettiContext.Provider>
  )
}

export const useConfetti = (): JSConfetti | null => React.useContext(ConfettiContext)
