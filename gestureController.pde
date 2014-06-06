import processing.serial.*;
import cc.arduino.*;

final boolean USE_OWN_CURVE = true;
final boolean ARDUINO_CONNECTED = false;

final int NUM_MOTORS = 3;

final int SFACTOR = 2;

boolean going[] = new boolean[NUM_MOTORS];
GesturePlayer[] gestPlayer = new GesturePlayer[NUM_MOTORS];
GestureRecorder gestRecorder;

Arduino arduino;
Motor[] motor = new Motor[NUM_MOTORS];

float[] drawAngle = new float[NUM_MOTORS];

void setup() {
    size(180*SFACTOR, 100*SFACTOR);
    background(102);

    println(Arduino.list());

    if(ARDUINO_CONNECTED)
	arduino = new Arduino(this, "/dev/ttyUSB0", 57600);

    //    motor[0] = new Motor(arduino, 12);
    //motor[1] = new Motor(arduino, 7);

    for(int i = 0; i < motor.length; i++){
	if(ARDUINO_CONNECTED)
	    motor[i] = new Motor(arduino, 10-NUM_MOTORS+i);
	drawAngle[i] = 180;
    }

    for(int i = 0; i < gestPlayer.length; i++){
	if(USE_OWN_CURVE)
	    gestPlayer[i] = new GesturePlayer("data.csv");
	else
	    gestPlayer[i] = new GesturePlayer("curves/timeCurve.csv");
	going[i] = false;
    }
    gestRecorder = new GestureRecorder("data.csv");
}

void draw() {
    thread("readPipe");
    background(100);
    
    if (mousePressed == false) {
	for(int i = 0; i < gestPlayer.length; i++){
	    if(going[i]){
		going[i] = !(gestPlayer[i].update(millis()));
		drawAngle[i] = gestPlayer[i].getPosition();
	    }
	}
    }
    else{
	if(pmouseX != mouseX){
	    for(int i = 0; i < gestPlayer.length; i++)
		drawAngle[i] = constrain(mouseX/SFACTOR,0,180);
	    //		drawAngle[i] = mouseX*.01;
	    gestRecorder.addPosition(drawAngle[0]);
	}
    }
    for(int i = 0; i < 180; i+=5){
	stroke(0);
	if(i%(15) == 0)
	    strokeWeight(1);
	else
	    strokeWeight(.1);
	line(i*SFACTOR,0,i*SFACTOR,height);
    }
    stroke(255,0,0);
    strokeWeight(2);
    line(mouseX,0,mouseX,height);

    translate(width/2, height/2);
    //    rotate(drawAngle[0] + PI);
    rotate(radians(drawAngle[0] + 180));
    noStroke();
    ellipse(0,0,15,15);
    rect(0, -2, 35, 4);

    if(ARDUINO_CONNECTED)
	for(int i = 0; i < motor.length; i++)
	    motor[i].move(arduino,int(drawAngle[i])); //CHECK RANGE MAY NOT BE FULL
    //	motor[i].move(arduino,int(drawAngle[i]*57)); //CHECK RANGE MAY NOT BE FULL
}
 
void keyReleased(){
    if(key == '1')
	going[0] = true;
    if(key == '2')
	going[1] = true;
    if(key == '3')
	going[2] = true;
    if(key == 'q')
	exit();
}

void mousePressed(){
    gestRecorder.clear();
}

void mouseReleased(){
    for(int i = 0; i < gestPlayer.length; i++){
	going[i] = false;
	gestPlayer[i].init("data.csv");
    }
}


void readPipe() {
    String[] s = loadStrings("sharingPlace.tmp");
    if(int(s[0]) == 1)
       going[0] = true;
}
