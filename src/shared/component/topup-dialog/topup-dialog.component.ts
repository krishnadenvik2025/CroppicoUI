import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { environment } from 'src/environments/environment';
import { APIS } from 'src/shared/model/api.model';

@Component({
  selector: 'app-topup-dialog',
  templateUrl: './topup-dialog.component.html',
  styleUrls: ['./topup-dialog.component.scss']
})
export class TopupDialogComponent implements OnInit {
  public topup_status: string = 'INFO';
  public url = environment.api;
  public intervalId: any;



  constructor(private http: HttpClient, @Inject(MAT_DIALOG_DATA) public dialogData: any, public dialogRef: MatDialogRef<any>) { }

  ngOnInit(): void {

  }

  async topupWaterFn(status: string) {
    await this.httpPost(APIS.TOPUP, { status });
    this.topup_status = 'IN-PROGRESS';
    if (status == 'stop') {
      this.topup_status = 'STOP';
      this.stopInterval();
      await this.delay(1000 * 3);
      return;
    }
    this.startInterval();
  }

  startInterval() {
    this.intervalId = setInterval(async () => {
      let res: any = await this.httpGet(APIS.TOPUP_RESULT);
      if (res?.result == true) {
        this.topup_status = 'DONE';
        this.stopInterval();
        await this.delay(1000 * 3);
        // this.dialogRef.close();
      }
      if (res?.result == 'clog') {
        this.topup_status = 'CLOG';
        this.stopInterval();
        await this.delay(1000 * 3);
      }
      if (res?.result == 'error') {
        this.topup_status = 'FAILED';
        this.stopInterval();
        await this.delay(1000 * 3);
        // this.dialogRef.close();
      }
    }, 1000 * 5);
  }

  // delay function
  delay = (delay: any) => new Promise((resolve, reject) => {
    setTimeout(() => resolve(true), delay);
  });

  // Get Api Call
  httpGet(endPoint: string) {
    return new Promise((resolve, reject) => {
      this.http.get<any>(this.url + "/" + endPoint).subscribe({
        next: data => {
          resolve(data);
        },
        error: error => {
          console.log(endPoint + " Api error");
          reject([]);
        }
      });
    });
  }

  // Post Api Call
  httpPost(method: string, body: any) {
    console.log("Http Post : ", method, body);
    return new Promise((resolve, reject) => {
      this.http.post<any>(this.url + "/" + method, body).subscribe({
        next: data => {
          resolve(data);
        },
        error: error => {
          console.log(method + " Api error");
          reject([]);
        }
      });
    });
  }

  stopInterval() {
    clearInterval(this.intervalId);
  }


  async userError() {
    this.httpPost(APIS.USER_ERROR_RESET, { reset: true });
    this.dialogRef.close();

  }

}
