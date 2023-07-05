import { type ReactNode } from 'react'
interface ConditionalWrapperProps {
  condition: boolean
  wrapper: Function
  children: ReactNode
}

const ConditionalWrapper = ({ condition, wrapper, children }: ConditionalWrapperProps): JSX.Element => {
  return (
    condition ? wrapper(children) : children
  )
}
export default ConditionalWrapper
