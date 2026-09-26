import { Button, type ButtonProps } from '@mui/material'
import { Link as RouterLink, useInRouterContext } from 'react-router-dom'

type RouterButtonLinkProps = Omit<ButtonProps, 'component' | 'href'> & {
  to: string
}

/**
 * Keeps application navigation in the SPA while allowing focused component
 * tests to render a page without a router provider.
 */
export function RouterButtonLink({ to, ...props }: RouterButtonLinkProps) {
  const hasRouter = useInRouterContext()

  if (!hasRouter) {
    return <Button component="a" href={to} {...(props as ButtonProps<'a'>)} />
  }

  return <Button component={RouterLink} to={to} {...(props as Omit<ButtonProps<typeof RouterLink>, 'to'>)} />
}
