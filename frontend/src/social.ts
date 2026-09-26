const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type SocialProfile = { id: string; name: string; nickname: string | null; biography: string | null; visible_to_clients: boolean | null; biography_moderation_status: string | null; biography_moderation_reason: string | null; has_image: boolean; follower_count: number; following_count: number; is_following: boolean; currently_present: boolean }
export type SocialPost = { id: string; author_name: string; content: string; visibility: 'private' | 'shared'; moderation_status: 'visible' | 'hidden'; moderation_reason: string | null; created_at: string }
export type ProfileSummary = { id: string; name: string; nickname: string | null; has_image: boolean }
export type PostComment = { id: string; author: ProfileSummary; content: string; created_at: string; is_own: boolean; moderation_status: string | null; moderation_reason: string | null }
export type PostDetail = { post: SocialPost; author: ProfileSummary; like_count: number; liked_by_viewer: boolean; comments: PostComment[] }

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers: { Authorization: `Bearer ${token}`, ...init?.headers } })
  if (!response.ok) throw new Error('Não foi possível concluir esta ação. Tente novamente.')
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
export const getOwnSocialProfile = (token: string) => request<SocialProfile>('/social-profiles/me', token)
export const updateOwnSocialProfile = (token: string, data: Partial<Pick<SocialProfile, 'nickname' | 'biography' | 'visible_to_clients'>>) => request<SocialProfile>('/social-profiles/me', token, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
export const uploadProfileImage = (token: string, file: File) => request<void>('/social-profiles/me/image', token, { method: 'PUT', headers: { 'Content-Type': 'application/octet-stream' }, body: file })
export const removeProfileImage = (token: string) => request<void>('/social-profiles/me/image', token, { method: 'DELETE' })
export const getSocialProfile = (token: string, id: string) => request<SocialProfile>(`/social-profiles/profiles/${id}`, token)
export const getProfilePosts = (token: string, id: string) => request<SocialPost[]>(`/social-profiles/profiles/${id}/posts`, token)
export const followProfile = (token: string, id: string, follow: boolean) => request<SocialProfile>(`/social-profiles/profiles/${id}/follow`, token, { method: follow ? 'PUT' : 'DELETE' })
export const getPostDetail = (token: string, id: string) => request<PostDetail>(`/social-profiles/posts/${id}`, token)
export const setPostLike = (token: string, id: string, liked: boolean) => request<PostDetail>(`/social-profiles/posts/${id}/like`, token, { method: liked ? 'PUT' : 'DELETE' })
export const addPostComment = (token: string, id: string, content: string) => request<PostComment>(`/social-profiles/posts/${id}/comments`, token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content }) })
export const deletePostComment = (token: string, id: string) => request<void>(`/social-profiles/comments/${id}`, token, { method: 'DELETE' })
export const profileImageUrl = (id: string) => `${apiBaseUrl}/social-profiles/profiles/${id}/image`
