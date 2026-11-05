import {Fragment, useEffect, useRef, useState} from 'react'
import {useNavigate} from 'react-router-dom'
import {ArrowUpRight, Bot, Download, FileText, LoaderCircle, Maximize2, MessageCircle, Send, X} from 'lucide-react'
import {api} from '../api'

type ChatProject={
  id:string
  name:string
  url:string
  domain:string
  organization:string
  status:string
  project_type:string
  mission_problem:string
  description:string
  datasets:string[]
  technologies:string[]
  reliability:number
  usefulness:string
}
type ChatResponse={id:string;answer:string;projects:ChatProject[];suggested_questions:string[];model:string;mode:string}
type ChatMessage={role:'user'|'assistant';content:string;projects?:ChatProject[];mode?:string;model?:string}
export type LibrarianSession={
  question:string
  messages:ChatMessage[]
  suggestions:string[]
  pending:boolean
  error:string
  hasAssistantReply:boolean
  setQuestion:(question:string)=>void
  ask:(text?:string)=>Promise<void>
}

const starterQuestions=[
  'List projects for predictive maintenance.',
  'Build a workflow from existing maintenance data.',
  'Which projects are seeking collaborators?'
]
const commonQuestions=[
  ...starterQuestions,
  'What datasets are available for logistics workflows?',
  'What tools already support budget execution dashboards?',
  'Which parts of this workflow should I add or omit?',
  'What projects use Python or React?',
  'Who owns the closest matching capability?'
]
const compact=(text:string)=>text.length>1800?text.slice(0,1800)+'...':text
const blockStart=/^(```|#{1,6}\s+|[-*]\s+|\d+\.\s+|>\s*)/
const chatTitle='Librarian'

function renderInline(text:string) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part,index)=>{
    if(part.startsWith('**')&&part.endsWith('**'))return <strong key={index}>{part.slice(2,-2)}</strong>
    if(part.startsWith('`')&&part.endsWith('`'))return <code key={index}>{part.slice(1,-1)}</code>
    return <Fragment key={index}>{part}</Fragment>
  })
}

function MarkdownText({text}:{text:string}) {
  const lines=text.split(/\r?\n/)
  const blocks=[]
  for(let index=0;index<lines.length;) {
    const line=lines[index].trimEnd()
    if(!line.trim()) {index++;continue}
    if(line.trim().startsWith('```')) {
      const code:string[]=[]
      index++
      while(index<lines.length&&!lines[index].trim().startsWith('```')) {code.push(lines[index]);index++}
      if(index<lines.length)index++
      blocks.push(<pre key={blocks.length}><code>{code.join('\n')}</code></pre>)
      continue
    }
    const heading=line.match(/^#{1,6}\s+(.+)$/)
    if(heading) {
      const level=Math.min(4, Math.max(2, line.match(/^#+/)?.[0].length ?? 4))
      if(level===2)blocks.push(<h2 key={blocks.length}>{renderInline(heading[1])}</h2>)
      else if(level===3)blocks.push(<h3 key={blocks.length}>{renderInline(heading[1])}</h3>)
      else blocks.push(<h4 key={blocks.length}>{renderInline(heading[1])}</h4>)
      index++
      continue
    }
    if(/^\*\*[^*]+\*\*:?\s*$/.test(line.trim())) {
      blocks.push(<h4 key={blocks.length}>{renderInline(line.trim().replace(/:$/,''))}</h4>)
      index++
      continue
    }
    if(line.trim().startsWith('>')) {
      const quoted:string[]=[]
      while(index<lines.length&&lines[index].trim().startsWith('>')) {quoted.push(lines[index].trim().replace(/^>\s*/,''));index++}
      blocks.push(<blockquote key={blocks.length}>{quoted.map((item,quoteIndex)=><p key={quoteIndex}>{renderInline(item)}</p>)}</blockquote>)
      continue
    }
    if(/^[-*]\s+/.test(line.trim())) {
      const items:string[]=[]
      while(index<lines.length&&/^[-*]\s+/.test(lines[index].trim())) {items.push(lines[index].trim().replace(/^[-*]\s+/,''));index++}
      blocks.push(<ul key={blocks.length}>{items.map((item,itemIndex)=><li key={itemIndex}>{renderInline(item)}</li>)}</ul>)
      continue
    }
    if(/^\d+\.\s+/.test(line.trim())) {
      const items:string[]=[]
      while(index<lines.length&&/^\d+\.\s+/.test(lines[index].trim())) {items.push(lines[index].trim().replace(/^\d+\.\s+/,''));index++}
      blocks.push(<ol key={blocks.length}>{items.map((item,itemIndex)=><li key={itemIndex}>{renderInline(item)}</li>)}</ol>)
      continue
    }
    const paragraph=[line.trim()]
    index++
    while(index<lines.length&&lines[index].trim()&&!blockStart.test(lines[index].trim())) {paragraph.push(lines[index].trim());index++}
    blocks.push(<p key={blocks.length}>{renderInline(paragraph.join(' '))}</p>)
  }
  return <div className="chat-markdown">{blocks}</div>
}

function transcript(messages:ChatMessage[]) {
  return messages.map(message=>`${message.role==='user'?'User':chatTitle}:\n${message.content}`).join('\n\n')
}

function escapePdfText(text:string) {
  return text.replace(/\\/g,'\\\\').replace(/\(/g,'\\(').replace(/\)/g,'\\)')
}

function makePdf(text:string) {
  const lines=text.replace(/[^\x09\x0a\x0d\x20-\x7e]/g,'?').replace(/\r/g,'').split('\n').flatMap(line=>{
    const chunks:string[]=[]
    for(let index=0;index<line.length;index+=86)chunks.push(line.slice(index,index+86))
    return chunks.length?chunks:['']
  })
  const pages:string[]=[]
  for(let index=0;index<lines.length;index+=42)pages.push(lines.slice(index,index+42).map((line,lineIndex)=>`BT /F1 10 Tf 50 ${760-lineIndex*16} Td (${escapePdfText(line)}) Tj ET`).join('\n'))
  const objects=[
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${pages.map((_,index)=>`${3+index*2} 0 R`).join(' ')}] /Count ${pages.length} >>`,
    ...pages.flatMap((page,index)=>[
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 ${3+pages.length*2} 0 R >> >> /Contents ${4+index*2} 0 R >>`,
      `<< /Length ${page.length} >>\nstream\n${page}\nendstream`,
    ]),
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]
  const header='%PDF-1.4\n'
  let body=header
  const offsets=[0]
  objects.forEach((object,index)=>{offsets.push(body.length);body+=`${index+1} 0 obj\n${object}\nendobj\n`})
  const xref=body.length
  body+=`xref\n0 ${objects.length+1}\n0000000000 65535 f \n${offsets.slice(1).map(offset=>String(offset).padStart(10,'0')+' 00000 n ').join('\n')}\n`
  body+=`trailer\n<< /Size ${objects.length+1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`
  return body
}

function downloadFile(filename:string, mime:string, content:string) {
  const blob=new Blob([content],{type:mime})
  const url=URL.createObjectURL(blob)
  const link=document.createElement('a')
  link.href=url
  link.download=filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function exportTranscript(messages:ChatMessage[], format:'txt'|'doc'|'pdf') {
  const text=transcript(messages)
  if(format==='txt')downloadFile('librarian-chat.txt','text/plain;charset=utf-8',text)
  if(format==='doc')downloadFile('librarian-chat.doc','application/msword;charset=utf-8',`<html><body><pre>${text.replace(/[&<>]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[char]!))}</pre></body></html>`)
  if(format==='pdf')downloadFile('librarian-chat.pdf','application/pdf',makePdf(text))
}

export function useLibrarianSession(user:string):LibrarianSession {
  const [question,setQuestion]=useState('')
  const [messages,setMessages]=useState<ChatMessage[]>([])
  const [suggestions,setSuggestions]=useState(commonQuestions)
  const [pending,setPending]=useState(false)
  const [error,setError]=useState('')
  const hasAssistantReply=messages.some(message=>message.role==='assistant')

  useEffect(()=>{
    setQuestion('')
    setMessages([])
    setSuggestions(commonQuestions)
    setPending(false)
    setError('')
  }, [user])

  async function ask(text=question) {
    const trimmed=text.trim()
    if(!trimmed||pending)return
    setPending(true);setError('');setQuestion('')
    const history=messages.slice(-8).map(message=>({role:message.role,content:compact(message.content)}))
    setMessages(previous=>[...previous,{role:'user',content:trimmed}])
    try {
      const response=await api<ChatResponse>('/chat/catalog',user,{method:'POST',body:JSON.stringify({question:trimmed,history})})
      setMessages(previous=>[...previous,{role:'assistant',content:response.answer,projects:response.projects,mode:response.mode,model:response.model}])
      setSuggestions([...response.suggested_questions,...commonQuestions])
    } catch(e) {
      setError(e instanceof Error?e.message:'Unable to ask the catalog chatbot.')
    } finally {
      setPending(false)
    }
  }

  return {question,messages,suggestions,pending,error,hasAssistantReply,setQuestion,ask}
}

function LibrarianChat({session, presentation='floating', onClose, onExpand}:{session:LibrarianSession; presentation?:'floating'|'page'; onClose?:()=>void; onExpand?:()=>void}) {
  const inputRef=useRef<HTMLTextAreaElement|null>(null)
  const {question,messages,suggestions,pending,error,hasAssistantReply,setQuestion,ask}=session

  return <section className={'catalog-chat-panel '+presentation} aria-label={chatTitle}>
      <header><div><span><Bot size={16}/>{chatTitle}</span><small>Ask the current database for projects, data, and workflows.</small></div><div className="catalog-chat-actions">{hasAssistantReply&&<div className="catalog-chat-export" aria-label="Export chat"><button title="Export TXT" aria-label="Export chat as TXT" onClick={()=>exportTranscript(messages,'txt')}><FileText size={16}/><span>TXT</span></button><button title="Export DOC" aria-label="Export chat as DOC" onClick={()=>exportTranscript(messages,'doc')}><Download size={16}/><span>DOC</span></button><button title="Export PDF" aria-label="Export chat as PDF" onClick={()=>exportTranscript(messages,'pdf')}><Download size={16}/><span>PDF</span></button></div>}{onExpand&&<button aria-label="Open full Librarian page" onClick={onExpand}><Maximize2 size={18}/></button>}{onClose&&<button aria-label="Close Librarian" onClick={onClose}><X size={18}/></button>}</div></header>
      <div className="catalog-chat-body">
        {!messages.length&&<div className="catalog-chat-empty"><strong>What are you trying to build?</strong><p>Start with one of these, or ask for an end-to-end workflow.</p><div>{starterQuestions.map(item=><button key={item} onClick={()=>void ask(item)}>{item}</button>)}</div></div>}
        {messages.map((message,index)=><article key={index} className={'chat-message '+message.role}>{message.role==='assistant'?<MarkdownText text={message.content}/>:<p>{message.content}</p>}{message.projects?.length?<div className="chat-projects">{message.projects.slice(0,5).map(project=><a key={project.id} href={project.url}><div><strong>{project.name}</strong><span>{project.organization} · {project.domain}</span><p>{project.mission_problem}</p><small>{project.reliability}% useful · {project.usefulness} reliability · {project.status}</small></div><ArrowUpRight size={14}/></a>)}</div>:null}</article>)}
        {messages.length>0&&!pending&&<div className="catalog-chat-followups" aria-label="Suggested follow-up questions">{suggestions.slice(0,3).map(item=><button key={item} onClick={()=>void ask(item)}>{item}</button>)}</div>}
        {pending&&<div className="chat-message assistant loading-row"><LoaderCircle className="spin" size={16}/>Thinking through matching projects and workflow pieces…</div>}
        {error&&<div className="catalog-chat-error" role="alert">{error}</div>}
      </div>
      <form onSubmit={event=>{event.preventDefault();void ask()}}>
        <div className="chat-input-wrap">
          <textarea ref={inputRef} aria-label="Ask the Librarian" rows={presentation==='page'?3:2} maxLength={1200} placeholder="What are you looking for?" value={question} onChange={event=>setQuestion(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();void ask();setTimeout(()=>inputRef.current?.focus(),0)}}}/>
        </div>
        <button aria-label="Send question" disabled={pending||!question.trim()}><Send size={17}/></button>
      </form>
    </section>
}

export function LibrarianPage({session}:{session:LibrarianSession}) {
  return <section className="librarian-page"><LibrarianChat session={session} presentation="page"/></section>
}

export function CatalogChatBubble({session}:{session:LibrarianSession}) {
  const [open,setOpen]=useState(false)
  const navigate=useNavigate()
  return <div className={'catalog-chat '+(open?'open':'')}>
    {open&&<LibrarianChat session={session} presentation="floating" onExpand={()=>{setOpen(false);navigate('/librarian')}} onClose={()=>setOpen(false)}/>}
    <button className="catalog-chat-toggle" aria-label={open?'Close Librarian':'Open Librarian'} onClick={()=>setOpen(value=>!value)}>{open?<X size={23}/>:<MessageCircle size={25}/>}</button>
  </div>
}
