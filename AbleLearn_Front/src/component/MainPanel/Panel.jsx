
import {useRef} from 'react'
import './Panel.css'
import UserInput from '../UserInput/UserInput'
import ChatPanel from '../Chat/ChatPanel';
import GameStatePanel from '@component/GameState/GameStatePanel';

function Panel(){
    const endPanel = useRef(null);
    var turn = 10;
    const handleDownScroll = ()=>{
        endPanel.current.scrollIntoView({behavior:'smooth'});
    }
    return(
        <div className='Page'>
            <div className="Date">
                    Current Turn:{turn}
            </div>
            <div className="MainPanel">
                <div className="TitlePanel">
                    <h1>10-Turn TRPG Game</h1>
                </div>
                <div className="MainState">
                    <GameStatePanel/>         
                </div>
                <div className="MainChat">
                    <ChatPanel/>
                </div>
                <div className="MainInput">
                    <UserInput/>
                </div>
            </div>
            <div ref={endPanel}></div>
        </div>
    )
}

export default Panel