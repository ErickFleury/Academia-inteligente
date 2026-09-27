import type { FeedPage, ProgressUpdate } from './progress'
import type { PostDetail } from './social'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
async function request<T>(path: string, token: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: 'no-store', headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error('Não foi possível carregar as publicações.')
  return response.json() as Promise<T>
}
export const getInstructorFeed = (token: string, cursor?: string) => request<FeedPage>(`/instructor/social/feed?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`, token)
export const getInstructorPostDetail = (token: string, id: string) => request<PostDetail>(`/instructor/social/posts/${id}`, token)
export async function fetchInstructorPostImage(token: string, postId: string, imageId: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/instructor/social/posts/${postId}/images/${imageId}`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error('Não foi possível carregar a imagem da publicação.')
  return URL.createObjectURL(await response.blob())
}
export type { ProgressUpdate }

export async function fetchInstructorCommentImage(token: string, postId: string, commentId: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/instructor/social/posts/${postId}/comments/${commentId}/image`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error('Não foi possível carregar a imagem do comentário.')
  return URL.createObjectURL(await response.blob())
}
