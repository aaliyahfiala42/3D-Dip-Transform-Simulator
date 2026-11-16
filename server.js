const express = require('express');
const path = require('path');
const multer = require('multer');
const fs = require('fs');
const crypto = require('crypto');

const app = express();

const {spawn } = require('child_process');

const PYTHON = path.join(__dirname, '.venv', 'bin', 'python');
const SCRIPTS = path.join(__dirname, 'scripts');
const DATA = path.join(__dirname, 'data');

const PORT = 3013;


//standard ejs middleware
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.json());
app.use(express.urlencoded({extended:true}));
app.use(express.static(path.join(__dirname, 'public')));



fs.mkdirSync(DATA, {recursive:true});
//allow .obj/.csv/.txt uploads
const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 50*1024*1024, files: 1}
});


//run python scripts via jobs 
const jobs = new Map();
function createJob(type) {
    const id = crypto.randomUUID();

    const dir = path.join(DATA, id);
    fs.mkdirSync(dir, {recursive:true});

    //type: simulation, reconstruction
    //statuses: queued, running, completed, failed
    //stage(simulation): starting simulation, voxelization, generating orientation, simulating dipping, creating dip dataset, simulator complete
    //stage(reconstruction): starting reconstruction, resampling, inverse optimization, clamping, construcing object, building output file
    const job = {
        id, dir,
        type, 
        status: 'queued', 
        progress:0, 
        stage: 'starting', 
        logs:[], 
        outouts:{}}
    jobs.set(id, job);
    return job;

}

//run python scripts (dip_simualtor.py or dip_reconstruction.py), collect output, get progress status, resolve on finish
function runPython(script, args, job) {
    return new Promise((resolve, reject )=> {
        
        const child = spawn(PYTHON,
            ['-u', path.join(SCRIPTS, script), ...args], 
            {cwd: job.dir, env: {...process.env, WEB_MODE:'1'}});

        let buffer='';

        function handleLine(line) {
            line=line.trim();
            if(!line) return;
            if(line.startsWith('PROGRESS:')){
                try{
                    const data = JSON.parse(line.slice(9));
                    job.stage = data.stage;
                    job.progress = data.percent;

                } catch {
                    jobs.logs.push(line);
                }
            }else{
                job.logs.push(line);
                job.logs = job.logs.slice(-20);

            }
        }

        child.stdout.on('data', chunk => {
            buffer += chunk.toString();
            const lines = buffer.split('\n');
            buffer = lines.pop();
            lines.forEach(handleLine);
        });

        child.stderr.on('data', chunk => {
            jobs.logs.push(chunk.toString());
            jobs.logs = jobs.logs.slice(-30);
        });
        child.on('error', reject);
        child.on('close', code => {
            if (buffer.trim()) {
                handleLine(buffer); 
            } 
            if(code === 0) { resolve() }
            else {reject(new Error(code))};
        });

    });
}

app.get('/', (req, res) => {
    res.render('home');
});

app.get('/howitworks', (req, res) => {
    res.render('howitworks');
});
app.get('/diy', (req, res) => {
    res.render('diy');
});
app.get('/references', (req, res) => {
    res.render('references');
});


//run scripts

app.post('/simulate', upload.single('obj'), (req, res)=>{
    //collect user inputs
    const shape = req.body.shape;
    const dips = String(req.body.dips);
    const noise = String(req.body.noise);
    const job = createJob('simulation');
    res.json({jobId: job.id});

    //if .obj file is uploaded, use that as shape instead
    if (req.file) {
        shape = path.join(job.dir, 'input.obj');
        fs.writeFileSync(shape, req.file.buffer);
    }


    //try running the simulator.py asynchrosly
    (async () => {
        try{
            await runPython('p1_dip_simulator.py',
                [shape, dips, noise],
                job);
            job.outputs = {obj: 'input.obj', csv: 'dip_data.csv'};
            job.status = 'completed';
            job.progress = 100;
            job.stage = 'dip dataset created';

    } catch (error) {
        job.status= 'failed';
        job.stage='simulation failed';
        job.logs.push(error.message);

    }
    })();

});


app.post('/reconstruct', upload.single('csv'), (req, res)=>{
    //collect user inputs

    const job = createJob('reconstruction');

    //if .obj file is uploaded, use that as shape instead
    if (req.file) {
        const inputPath = path.join(job.dir, 'dip_data.csv');
        fs.writeFileSync(inputPath, req.file.buffer);
    } else {
        const previous = jobs.get(req.body.sourceJob);
        fs.copyFileSync(path.join(previous.dir, 'dip_data.csv'), input);
    }

    res.json({jobId: job.id});

    //try running the simulator.py asynchrosly
    (async () => {
        try{
            await runPython('p2_dip_simulator.py',
                ['dip_data.csv'],
                job

            );
            
            jobs.status= 'completed';
            jobs.progress = 100;
            jobs.stage = 'reconstruction created';
            jobs.outputs = {obj: 'dip_reconstruction.obj' }

    } catch (error) {
        jobs.logs.push(error.message);
        job.status = 'failed';
        job.stage ='reconstruction failed';

    }
    })();

});

//get current job info
app.get('/job/:id', (req, res) => {
    const job = jobs.get(req.params.id);
    if(!job) return res.sendStatus(400);

    res.json({
        id: job.id,
        type: job.type,
        status:job.status,
        stage:job.stage,
        progress:job.progress,
        logs:job.logs.slice(-10),
        outputs:job.outputs
    });
});
// make script outputs downloadable
app.get('/data/:id/:name', (req, res) => {
    const job = jobs.get(req.params.id);
    if(!job) return res.sendStatus(404);

    const filename = req.params.name;
    res.sendFile(path.join(job.dir, filename));
});

//error handler
app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).json({ error: err.message });
});

app.listen(PORT, '127.0.0.1', () => {console.log(`http://localhost:${PORT}/`);});

