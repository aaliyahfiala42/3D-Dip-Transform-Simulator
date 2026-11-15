require('dotenv').config();
const express = require('express');
const path = require('path');
const app = express();

const PORT = 3013;

//standard ejs middleware
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.json());
app.use(express.urlencoded({extended:true}));
app.use(express.static(path.join(__dirname, 'public')));



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



//error handler
app.use((err, req, res, next)=>{
    console.error(err);
    req.status(err.status || 500).json({
        error:err.status && err.status < 500 ? err.message : "Uh oh."
    });

});


app.listen(PORT, '127.0.0.1', () => {console.log(`http://localhost:${PORT}/`);});

