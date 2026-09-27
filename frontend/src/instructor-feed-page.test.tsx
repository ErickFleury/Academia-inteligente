import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { InstructorFeedPage } from './instructor-feed-page'
import { InstructorPostDetailPage } from './instructor-post-detail-page'
const post = { id:'post', author_name:'Maria Silva',content:'Publicação pública',created_at:'2026-09-27T12:00:00Z',like_count:2,comment_count:1,images:[{id:'image',width:1,height:1}] }
const ok=(value:unknown)=>({ok:true,json:async()=>value})
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks()})
function images() { URL.createObjectURL=vi.fn(()=> 'blob:synthetic');URL.revokeObjectURL=vi.fn() }
test('shared read-only feed renders permitted media and exposes only navigation',async()=>{
  images();const open=vi.fn()
  const fetchMock=vi.fn(async(url:string)=>url.includes('/images/')?{ok:true,blob:async()=>new Blob(['fake'])}:ok({items:[post],next_cursor:null,end_reached:true}))
  vi.stubGlobal('fetch',fetchMock)
  render(<MemoryRouter><InstructorFeedPage accessToken="token" onSignOut={vi.fn()} onOpenPost={open}/></MemoryRouter>)
  expect(await screen.findByRole('img',{name:'Imagem 1 da publicação de Maria Silva'})).toHaveAttribute('src','blob:synthetic')
  expect(screen.queryByRole('button',{name:/Curtir|Editar publicação|Publicar/})).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Abrir comentários'}));expect(open).toHaveBeenCalledWith('post')
  expect(fetchMock.mock.calls.some(([url])=>url.includes('/instructor/social/posts/post/images/image'))).toBe(true)
})
test('failed feed ends processing and supports retry',async()=>{
  let failed=true;vi.stubGlobal('fetch',vi.fn(async()=>failed?{ok:false,status:503}:ok({items:[],next_cursor:null,end_reached:true})))
  render(<MemoryRouter><InstructorFeedPage accessToken="token" onSignOut={vi.fn()} onOpenPost={vi.fn()}/></MemoryRouter>)
  await screen.findByText('Não foi possível carregar as publicações.')
  expect(screen.queryByText('Carregando publicações')).not.toBeInTheDocument()
  failed=false;fireEvent.click(screen.getByRole('button',{name:'Recarregar publicações'}))
  await screen.findByText('Nenhuma publicação disponível')
})
test('detail includes post and comment images with no interaction composer',async()=>{
  images()
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.includes('/images/')||url.endsWith('/image')?{ok:true,blob:async()=>new Blob(['fake'])}:ok({post,author:{name:'Maria Silva'},like_count:2,comments:[{id:'comment',author:{name:'Ana'},content:'Comentário',image:{id:'comment',width:1,height:1}}]})))
  render(<MemoryRouter><InstructorPostDetailPage accessToken="token" postId="post" onSignOut={vi.fn()}/></MemoryRouter>)
  await screen.findByRole('img',{name:'Imagem 1 da publicação de Maria Silva'})
  await screen.findByRole('img',{name:'Imagem do comentário de Ana'})
  expect(screen.getByText('1 comentários')).toBeInTheDocument()
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
})
