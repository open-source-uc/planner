interface InfoProps {
  message: string
}

export function Info ({ message }: InfoProps): JSX.Element {
  return <div className="group relative flex justify-center">
     <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="11" cy="11" r="10" stroke="black" strokeOpacity="0.5" strokeWidth="2"/>
      <line x1="11" y1="9" x2="11" y2="17" stroke="black" strokeOpacity="0.5" strokeWidth="2"/>
      <line x1="12" y1="6" x2="10" y2="6" stroke="black" strokeOpacity="0.5" strokeWidth="2"/>
    </svg>
    <span className={'relative z-10  transition-all  scale-0 group-hover:scale-100'}>
      <div className="absolute left-2.5 top-1 w-4 h-4 bg-gray-800 rotate-45 rounded" />
      <span className={'absolute left-4 -top-1  w-48 z-10 rounded bg-gray-800 p-2 text-xs text-white'}>
        {message}
      </span>
    </span>
    </div>
}
