const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Configuration
const VIDEO_FILE_PATH = '/home/cofucan/Videos/proj_demo.mp4';
const LOCAL_URL = 'http://127.0.0.1:8000';
const REMOTE_URL = 'http://api.helpmeout.tech';
const BLOB_SIZE = 1 * 1024 * 1024;  // 1MB by default. Adjust as needed.
const USERNAME = 'user13';

let URL;
if (process.argv[2] === '--local') {
    URL = LOCAL_URL;
} else if (process.argv[2] === '--remote') {
    URL = REMOTE_URL;
} else {
    console.error('Invalid argument. Use "--local" or "--remote"');
    process.exit(1);
}

const GET_VIDEO_ID_URL = `${URL}/start-recording/`;
const ENDPOINT_URL = `${URL}/upload-blob/`;

async function getVideoId(username) {
    try {
        const response = await axios.post(GET_VIDEO_ID_URL, { username });
        console.log(response.data);
        return response.data.video_id;
    } catch (error) {
        console.error(`Failed to get video ID: ${error}`);
    }
}

async function sendBlob(videoId, blob, blobId, isLast) {
    const data = {
        username: USERNAME,
        video_id: videoId,
        blob_index: blobId,
        blob_object: blob.toString('base64'),
        is_last: isLast
    };

    try {
        const response = await axios.post(ENDPOINT_URL, data, {
            headers: { 'Content-Type': 'application/json' }
        });
        console.log(response.data);
    } catch (error) {
        console.error(`Failed to send blob: ${error}`);
    }
}

async function main() {
    const videoId = await getVideoId(USERNAME);

    const videoStream = fs.createReadStream(VIDEO_FILE_PATH, { highWaterMark: BLOB_SIZE });

    let blobId = 1;

    videoStream.on('data', (chunk) => {
        const isLast = chunk.length < BLOB_SIZE;
        sendBlob(videoId, chunk, blobId, isLast);
        blobId += 1;
    });

    videoStream.on('end', () => {
        console.log('Finished sending blobs');
    });
}

main();
