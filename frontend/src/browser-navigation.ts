/** Replace transient authentication pages instead of adding them to Back history. */
export function replaceLocation(url: URL): void {
  window.location.replace(url.href)
}
