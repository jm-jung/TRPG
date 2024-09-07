import {useState, useCallback, useEffect, useRef, useContext} from 'react';
import './ChatPanel.css';
import ChatItem from './ChatItem';


function ChatPanel(){
    const [messages, setMessage] = useState([{profile:{name:"유저", imgsrc:'/용사맛쿠키.png'}, content:"안녕하세요", time: "16:48"}]);
    const endWindow = useRef(null);
    const downScroll = ()=>{endWindow.current.scrollIntoView({behavior: 'smooth'});}
    useEffect(downScroll, [messages])
    const handleAddMessage = () => {
        setMessage(prev =>[...messages, {profile:
            {name:"마왕", imgsrc:"/마왕.png"}, 
        content:"흐하하하하하", 
        time: "16:50"}]);
    }
    // setMessage([{name:"a", content:"test", time:"1234"}, {name:"b", content:"test2", time:"1234"}])
    return(
        <div className="ChatPanel">
            {messages.map((message,index)=>{
                const {profile, content, time} = message;
                return(
                    <ChatItem 
                    key={index} 
                    profile={profile}
                    content={content} 
                    time={time}
                    />
                )
            })}
            <div ref={endWindow}></div>
            <button onClick={handleAddMessage}>t</button>
            <button className="downButton" onClick={downScroll}> ↓ </button>
        </div>
    )
}

export default ChatPanel