import { readFile } from 'fs';

function greet(name) {
    console.log('Hello ' + name);
}

class Animal {
    constructor(name) {
        this.name = name;
    }
    speak() {
        return this.name;
    }
}

const x = greet('world');
