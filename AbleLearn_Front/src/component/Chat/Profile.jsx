import 'react'

function Profile({profile}){
    return(
        <div className="profile">
            {console.log(profile.imgsrc)}
            <img src={profile.imgsrc} alt="사진" className='profilePicture'/>
            <div className='profileName'>{profile.name}</div>
        </div>
    )
}
export default Profile