import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { NgForm } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { KeypadComponent } from 'src/app/keypad/keypad.component';
import { environment } from 'src/environments/environment';
import { APIS } from 'src/shared/model/api.model';


@Component({
  selector: 'app-calibration-dialog',
  templateUrl: './calibration-dialog.component.html',
  styleUrls: ['./calibration-dialog.component.scss']
})
export class CalibrationDialogComponent implements OnInit {
  public url = environment.api;
  public isCalibrating = 'false';
  public intervalId: any;
  public isCalibrationDone = false;
  public isError = false;
  public PumpCalibStep = 'INFO';
  public isPumpLoader = false;
  public MeasuredValue = 0;
  public isDisable: boolean[] = [];
  public calibData: any;
  constructor (public dialogRef: MatDialogRef<CalibrationDialogComponent>,
    private http: HttpClient,
    @Inject(MAT_DIALOG_DATA) public dialogData: any,
    private modalService: NgbModal) {
  }

  ngOnInit (): void {
    this.init();
    console.log('dialogData', this.dialogData);
    this.sendProcessCount();
  }

  public async init () {
    // get ph and ec array 
    if (this.dialogData?.calibration == 'SENSOR') {
      const calibData: any = await this.httpGet(APIS.GET_CALIB_DATA + this.dialogData?.endPoint);
      this.calibData = calibData?.data;

    }
  }
  // send calibration data and solution name
  async sendCalibData (data: any, index?: any) {
    const obj = {
      "value": String(data.value),
      "solution": String(this.dialogData?.solution)
    };
    this.isCalibrating = 'true';

    // await this.delay(3000);
    // this.isCalibrating = 'false';
    // this.isCalibrationDone = true;
    // await this.delay(3000);
    // this.isCalibrationDone = false;
    await this.httpPost(APIS.SETTING_9, obj);
    this.startInterval(index);
  }


  // delay function
  delay = (delay: any) => new Promise((resolve, reject) => {
    setTimeout(() => resolve(true), delay);
  });

  // start pump function 
  async startPumpCalibration () {
    this.isPumpLoader = true;
    setTimeout(async () => {
      this.isPumpLoader = false;
      // this.isCalibrationDone = true;
      // await this.delay(1000 * 3);
      // this.isCalibrationDone = false;
      this.PumpCalibStep = 'ENTER VALUE';

    }, 1000 * 60);

    let key = this.dialogData?.solution == 'flow_sensor' ? 'water_pump' : this.dialogData?.solution;
    let pumpObj: any = {};
    pumpObj[`${key}`] = 1 + ":00";
    await this.httpPost(APIS.START_PUMP, pumpObj);
    // this.startInterval();


  }

  // send measured value function

  async sendMeasuredValue () {
    this.isCalibrating = 'true';
    this.PumpCalibStep = 'END';
    // await this.delay(3000);
    // this.isCalibrating = 'false';
    // this.PumpCalibStep = 'ENTER '
    // this.isCalibrationDone = true;
    const obj = {
      "value": String(this.MeasuredValue),
      "solution": String(this.dialogData?.solution)
    };
    await this.httpPost(APIS.SETTING_9, obj);
    this.startInterval();
    console.log('measured Value', String(this.MeasuredValue));
  }


  // To Send count of precessed values
  sendProcessCount () {
    const count = this.isDisable.filter(Boolean).length;
    if (count) {
      const obj = {
        "solution": String(this.dialogData?.solution),
        "count": String(count)
      };
      console.log('sendProcessCount', obj);

      this.httpPost(APIS.SEND_COUNT, obj);
    }
    this.stopInterval();
  }


  // To open keyboard component 
  open (form: NgForm, inputItem: any) {
    let tempFormVal = form.value;
    const modalRef = this.modalService.open(KeypadComponent, {
      size: 'sm',
      backdrop: 'static',
      centered: true,
      scrollable: false
    });
    console.log('tempFormVal[inputItem]', tempFormVal[inputItem]);
    modalRef.componentInstance.defVal = tempFormVal[inputItem];
    modalRef.componentInstance.passEntry.subscribe((receivedEntry: any) => {
      console.log("Received Data:", receivedEntry, tempFormVal);
      tempFormVal[inputItem] = receivedEntry;
      form.setValue(tempFormVal);
      modalRef.close();
    });
  }


  // Get Api Call
  httpGet (endPoint: string) {
    console.log("Http Get : ", endPoint);
    return new Promise((resolve, reject) => {
      this.http.get<any>(this.url + "/" + endPoint).subscribe({
        next: data => {
          resolve(data);
        },
        error: error => {
          console.log(endPoint + " Api error");
          resolve([]);
        }
      });
    });
  }
  // Post Api Call
  httpPost (method: string, body: any) {
    console.log("Http Post : ", method, body);
    return new Promise((resolve, reject) => {
      this.http.post<any>(this.url + "/" + method, body).subscribe({
        next: data => {
          resolve(data);
        },
        error: error => {
          console.log(method + " Api error");
          resolve([]);
        }
      });
    });
  }

  // Function to start setInterval call
  startInterval (index?: any) {
    this.intervalId = setInterval(async () => {
      let res: any = await this.httpGet(APIS.GET_RESULT);
      if (res?.result == true) {
        this.isCalibrating = 'false';
        this.isPumpLoader = false;
        this.isCalibrationDone = true;
        this.PumpCalibStep == 'SEND CALIB VALUE' ? this.PumpCalibStep = 'ENTER VALUE' : '';
        this.isDisable[index] = true;
        await this.delay(1000 * 3);
        // this.isCalibrationDone = false;
        
        this.stopInterval();
        this.PumpCalibStep == 'END' ? '' : '';
      }
      if (res?.result == 'error') {
        this.isCalibrating = '';
        this.isPumpLoader = false;
        this.isError = true;
        await this.delay(1000 * 3);
        // this.isError = false;
        this.stopInterval();
        // this.dialogRef.close();

      }

    }, 1000 * 5);
  }

  // Function to stop setInterval call
  stopInterval () {
    clearInterval(this.intervalId);
  }

}


