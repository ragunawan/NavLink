import {Fragment, useMemo, useRef, useState} from 'react'
import {ArrowUpRight, Bot, LoaderCircle, MessageCircle, Send, X} from 'lucide-react'
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
  datasets:string[]
  technologies:string[]
  reliability:number
  usefulness:string
}
type ChatResponse={id:string;answer:string;projects:ChatProject[];suggested_questions:string[];model:string;mode:string}
type ChatMessage={role:'user'|'assistant';content:string;projects?:ChatProject[];mode?:string;model?:string}

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
      blocks.push(<h4 key={blocks.length}>{renderInline(heading[1])}</h4>)
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

export function CatalogChatBubble({user}:{user:string}) {
  const [open,setOpen]=useState(false)
  const [question,setQuestion]=useState('')
  const [messages,setMessages]=useState<ChatMessage[]>([])
  const [suggestions,setSuggestions]=useState(commonQuestions)
  const [pending,setPending]=useState(false)
  const [error,setError]=useState('')
  const inputRef=useRef<HTMLTextAreaElement|null>(null)
  const completion=useMemo(()=>question.trim()?suggestions.find(item=>item.toLowerCase().startsWith(question.trim().toLowerCase())&&item.toLowerCase()!==question.trim().toLowerCase()):'', [question,suggestions])
  const completionTail=completion&&question?completion.slice(question.length):''

  async function ask(text=question) {
    const trimmed=text.trim()
    if(!trimmed||pending)return
    setOpen(true);setPending(true);setError('');setQuestion('')
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
      setTimeout(()=>inputRef.current?.focus(),0)
    }
  }

  return <div className={'catalog-chat '+(open?'open':'')}>
    {open&&<section className="catalog-chat-panel" aria-label="LinkBot">
      <header><div><span><Bot size={16}/>LinkBot</span><small>Ask the current database for projects, data, and workflows.</small></div><button aria-label="Close LinkBot" onClick={()=>setOpen(false)}><X size={18}/></button></header>
      <div className="catalog-chat-body">
        {!messages.length&&<div className="catalog-chat-empty"><strong>What are you trying to build?</strong><p>Start with one of these, or ask for an end-to-end workflow.</p><div>{starterQuestions.map(item=><button key={item} onClick={()=>void ask(item)}>{item}</button>)}</div></div>}
        {messages.map((message,index)=><article key={index} className={'chat-message '+message.role}>{message.role==='assistant'?<MarkdownText text={message.content}/>:<p>{message.content}</p>}{message.projects?.length?<div className="chat-projects">{message.projects.slice(0,3).map(project=><a key={project.id} href={project.url}><div><strong>{project.name}</strong><span>{project.organization} · {project.domain}</span><p>{project.mission_problem}</p><small>{project.reliability}% useful · {project.usefulness} reliability · {project.status}</small></div><ArrowUpRight size={14}/></a>)}</div>:null}</article>)}
        {messages.length>0&&!pending&&<div className="catalog-chat-followups" aria-label="Suggested follow-up questions">{suggestions.slice(0,3).map(item=><button key={item} onClick={()=>void ask(item)}>{item}</button>)}</div>}
        {pending&&<div className="chat-message assistant loading-row"><LoaderCircle className="spin" size={16}/>Thinking through matching projects and workflow pieces…</div>}
        {error&&<div className="catalog-chat-error" role="alert">{error}</div>}
      </div>
      <form onSubmit={event=>{event.preventDefault();void ask()}}>
        <div className="chat-input-wrap">
          {completion&&<button type="button" className="chat-completion" onClick={()=>setQuestion(completion)}>{completion}</button>}
          {completionTail&&<div className="chat-autofill" aria-hidden="true"><span>{question}</span>{completionTail}</div>}
          <textarea ref={inputRef} aria-label="Ask the catalog chatbot" rows={2} maxLength={1200} placeholder="What are you looking for?" value={question} onChange={event=>setQuestion(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();void ask()}}}/>
        </div>
        <button aria-label="Send question" disabled={pending||!question.trim()}><Send size={17}/></button>
      </form>
    </section>}
    <button className="catalog-chat-toggle" aria-label={open?'Close LinkBot':'Open LinkBot'} onClick={()=>setOpen(value=>!value)}>{open?<X size={23}/>:<MessageCircle size={25}/>}</button>
  </div>
}
