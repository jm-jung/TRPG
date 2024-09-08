import 'react'
import './ChatItem.css'
import Profile from './Profile'

function ChatItem({profile , content, time}){
    return(
        <div className="ChatItem">
            {profile.name==="유저" ? (
                <div className="userContainer">
                    <Profile profile={profile}/>
                    <div className="content">{content}</div>
                    <div className="timestamp">{time}</div>
                </div>
            ) : (
                <div className="enemyContainer">
                    <Profile profile={profile}/>
                    <div className="content">{content}</div>
                    <div className="timestamp">{time}</div>
                </div>
            )}
            
        </div>
    )
}

export default ChatItem