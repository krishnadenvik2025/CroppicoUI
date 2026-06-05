import {
  HttpClient
} from '@angular/common/http';
import {
  AfterViewInit,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output
} from '@angular/core';
import {
  FormControl,
  NgForm
} from '@angular/forms';
import {
  NgbModal
} from '@ng-bootstrap/ng-bootstrap';
import {
  environment
} from 'src/environments/environment';
import {
  KeypadComponent
} from '../keypad/keypad.component';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { CalibrationDialogComponent } from 'src/shared/component/calibration-dialog/calibration-dialog.component';
import { AuthComponent } from 'src/shared/component/auth/auth.component';
import { APIS } from 'src/shared/model/api.model';
import { ScreenSaverService } from 'src/core/screen-saver.service';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})

export class SettingsComponent implements OnInit, AfterViewInit, OnDestroy {
  url = environment.api;
  public myAngularxQrCode: string = "";
  active = 1;
  sno = "1234567";
  mode = "Custom";
  allSettings: any;
  mActive = false;
  wifinamelist: any[] = [];
  curWifiName: string = "";
  slaveVersion: any = "00.0";
  versionData: any;
  private intervalId: any;
  public screenSaverStatus: boolean = true;
  wtPumpSet: any = {
    ontime: 0,
    offtime: 0
  };
  pHSet: any = {
    phmin: 0.0,
    phmax: 0.0,
    phideal: 0.0,
    phsensor_setpoint: 0,
    phpump_setpoint: 0
  };
  eCSet: any = {
    ecmin: 0,
    ecideal: 0,
    ecsensor_setpoint: 0,
    ecpump_setpoint: 0

  };
  wtTempSet: any = {
    tempmax: 0,
    tempideal: 0,
    phdose: 0,
    ecdose: 0
  };
  suppPumpSet: any = {
    ec: 0,
    phinc: 0,
    phdec: 0,
    cycle: 0
  };
  screen_saver_setting: any = {
    status: false,
    interval_time: 0
  };
  systemFormControl = new FormControl('');
  screenSaverFormControl = new FormControl(false);
  @Output() screenSaverData: any = new EventEmitter();

  // Batch Settings
  currentBatchStatus: any = { batch: 0 };
  uiBatchMode: string = 'default';
  batchFormData: any = {};
  previousBatchesList: any[] = [];
  plantTypes: string[] = ['Basil', 'Lettuce', 'Tomato', 'Strawberry'];
  days: number[] = Array.from({length: 31}, (_, i) => i + 1);
  months: string[] = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  years: number[] = [2024, 2025, 2026, 2027, 2028, 2029, 2030];

  constructor(private modalService: NgbModal,
    private http: HttpClient,
    private dialog: MatDialog,
    private screensaver: ScreenSaverService) {
    this.myAngularxQrCode = 'tutsmake.com';
  }

  ngAfterViewInit(): void {

  }

  ngOnInit(): void {
    this.getSettings();
    this.getVersion();
    this.getWifiNames();
    this.getBatchStatus();
    this.getPreviousBatches();
    setTimeout(()=>{
      this.systemScreen(1);
    },100)
      this.intervalId =  setInterval(() => {
      this.getWifiNames();
      // this.light_1_state = !this.light_1_state;
    }, 10000);
  }

  //CALIBRATION POP UP

  openCalibarionPopup(endPoint: number, solution: string, type: string) {
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: true,
      minWidth: "200px",
      minHeight: '200px',
      data: {
        title: `Select Calibration Value`,
        endPoint,
        calibration: type,
        solution
      },
    };
    this.screensaver.updateScreenSaverStatus(false)
    const dialog = this.dialog.open(CalibrationDialogComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true)
      console.log(result);
    });


  }

  async sendSystemType() {
    const type = this.systemFormControl.value;
    if (type) {
      const obj = { type };
      await this.httpPost(APIS.SYSTEM_TYPE, obj);
    }
  }
  async getVersion() {
    let version: any = await new Promise((resolve, reject) => {
      this.http
        .get<any[]>(this.url + "/system/versioninfo").subscribe({
          next: data => {
            resolve(data);
          },
          error: error => {
            console.log(error);
            resolve(false);
          }
        });
    });
    this.versionData = version;
    this.slaveVersion = version["slave"];
    this.sno = version["serial"];

  }

  async systemScreen(index:any) {
    let payloadData;
    if(index == 1)
    {
      payloadData = {
        "screen":"settings",
        "status":"true"
      }
    }
    if(index == 2)
      {
        payloadData = {
          "screen":"settings",
          "status":"false"
        }
      }
    
    this.httpPost("system/screen", payloadData);

  }

  async getSettings() {
    let settingApiCallData: any = await new Promise((resolve, reject) => {
      this.http
        .get<any[]>(this.url + "/getsettings").subscribe({
          next: data => {
            resolve(data);
          },
          error: error => {
            console.log(error);
            resolve(false);
          }
        });
    });
    console.log('settingApiCallData', settingApiCallData);
    if (Object.keys(settingApiCallData).length && settingApiCallData != false) {
      this.allSettings = settingApiCallData;
      this.wtPumpSet = this.allSettings["water_pump_setting"];
      this.pHSet = this.allSettings["ph_setting"];
      this.eCSet = this.allSettings["ec_setting"];
      this.wtTempSet = {
        tempmax: this.allSettings["water_temperature_setting"].tempmax || 0,
        tempideal: this.allSettings["water_temperature_setting"].tempideal || 0,
        phdose: this.allSettings["water_temperature_setting"].phdose || 0,
        ecdose: this.allSettings["water_temperature_setting"].ecdose || 0
      };
      this.suppPumpSet = this.allSettings["supplement_pump_setting"];
      this.systemFormControl.setValue(this.allSettings["system_setting"].system_type);
      this.screenSaverFormControl.setValue(Boolean(Number(this.allSettings["system_setting"].screensaver_status)));
      this.screen_saver_setting.interval_time = Number(this.allSettings["system_setting"].screensaver_time);
    } else {
      console.log("Api error");
    }
  }


  async getWifiNames() {
  // const data = { "cur": "DENVIK AIRTEL", "res": ["Denvik_JIO2_4_EXT", "DENVIK AIRTEL", "JioFiber-Ped1o", "JioFiber-x3R2q", "JP Home", "MANI5", "VASKANNEN"] }
  // let k: any = data;


  // const moveToTop = k["res"];
  // const index = moveToTop?.indexOf(k["cur"]);
  // const element = moveToTop.splice(index, 1)[0];
  // moveToTop.unshift(element);
  // this.wifinamelist = moveToTop;
  // this.curWifiName = k["cur"];
  var wifinames = await new Promise((resolve, reject) => {
    this.http
      .get<any[]>(this.url + "/system/wifinames").subscribe({
        next: data => {
          let k: any = data;
          const moveToTop = k["res"];
          const index = moveToTop?.indexOf(k["cur"]);
          const element = moveToTop.splice(index, 1)[0];
          moveToTop.unshift(element);
          this.wifinamelist = moveToTop;
          this.curWifiName = k?.cur || '';
          resolve(data);
        },
        error: error => {
          console.log(error);
          resolve(false);
        }
      });
  });
  console.log(this.wifinamelist, this.curWifiName);
  // this.wifiname = wifinames;
  }

  async updateWaterPumpSettings(form: NgForm) {
    console.log('Water Pump Setting Data : ', form.value);
    await this.httpPost("settings/waterpump", form.value);
  }

  updatePhSettings(form: NgForm) {
    console.log('Ph Setting Data : ', form.value);
    this.httpPost("settings/ph", form.value);
  }

  updateEcSettings(form: NgForm) {
    console.log('Ph Setting Data : ', form.value);
    this.httpPost("settings/ec", form.value);
  }

  updateWaterTempSettings(form: NgForm) {
    console.log('Water Temp Setting Data : ', form.value);
    this.httpPost("settings/watertemp", form.value);
  }

  updateSuppPumpSettings(form: NgForm) {
    console.log('Supp Pump Setting Data : ', form.value);
    let tempsupp = form.value;
    // tempsupp["phdec"] = form.value.phinc
    this.httpPost("settings/supplementpump", tempsupp);
  }

  // maintWaterPump (state: boolean) {
  //   console.log("Maintenance Mode - Water Pump : " + state);
  //   this.httpPost("maintenance/control/1", { state: state });
  // }

  // maintPhUpPump (state: boolean) {
  //   console.log("Maintenance Mode - ph Up Pump : " + state);
  //   this.httpPost("maintenance/control/4", { state: state });
  // }

  // maintPhDownPump (state: boolean) {
  //   console.log("Maintenance Mode - ph Down Pump : " + state);
  //   this.httpPost("maintenance/control/5", { state: state });
  // }

  // maintEcPump (state: boolean) {
  //   console.log("Maintenance Mode - EC Pump : " + state);
  //   this.httpPost("maintenance/control/3", { state: state });
  // }

  // maintWaterChiller (state: boolean) {
  //   console.log("Maintenance Mode - Water Chiller : " + state);
  //   this.httpPost("maintenance/control/2", { state: state });
  // }

  settingMenuChange(opt: any) {
    if (opt.nextId == 6) {
      //activate maint
      // this.httpPost("maintenance/state/True", {});
    } else {
      //deactivate maint
      // this.httpPost("maintenance/state/False", {});
    }
    return;
  }

  open(form: NgForm, inputItem: any) {
    console.log("Opening Modal", form.value, inputItem);
    let tempFormVal = form.value;
    const modalRef = this.modalService.open(KeypadComponent, {
      size: 'sm',
      backdrop: 'static',
      centered: true,
      scrollable: false
    });
    const value = tempFormVal[inputItem] || 0;
    console.log('tempFormVal[inputItem]', tempFormVal[inputItem]);
    modalRef.componentInstance.defVal = tempFormVal[inputItem] || 0;
    modalRef.componentInstance.passEntry.subscribe((receivedEntry: any) => {
      console.log("RECEIVERD data", receivedEntry);

      const isValidFn = (obj: any) => {
        if (this.minMaxFn(obj)) {
          tempFormVal[inputItem] = receivedEntry;
          form.setValue(tempFormVal);
        } else {
          tempFormVal[inputItem] = value;
          form.setValue(tempFormVal);
        }
      };
      console.log("Received Data:", receivedEntry, tempFormVal);
      let obj = {};
      switch (true) {
        case inputItem == 'phmin':
          obj = {
            min: 0.0,
            max: 10.0,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'phmax':
          obj = {
            min: 0.0,
            max: 10.0,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'phideal':
          obj = {
            min: 0.0,
            max: 1.0,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'phsensor_setpoint':
          obj = {
            min: 0,
            max: 999999,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'phpump_setpoint':
          obj = {
            min: 0.0,
            max: 4.0,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'ecmin':
          obj = {
            min: 0,
            max: 3000,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'ecideal':
          obj = {
            min: 0,
            max: 900,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'ecsensor_setpoint':
          obj = {
            min: 0,
            max: 500,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'ecpump_setpoint':
          obj = {
            min: 0,
            max: 300,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'tempideal':
          obj = {
            min: 25,
            max: 35,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;

        case inputItem == 'phdose':
          obj = {
            min: 0.0,
            max: 10.0,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;
        case inputItem == 'ecdose':
          obj = {
            min: 0,
            max: 10,
            value: Number(receivedEntry)
          };
          isValidFn(obj);
          break;

        default:
          tempFormVal[inputItem] = receivedEntry;
          form.setValue(tempFormVal);
          break;
      }
      modalRef.close();
    });
  }

  minMaxFn(num: any) {
    return (num.value >= num.min && num.value <= num.max);
  }

  httpPost(method: string, body: any) {
    console.log("Http Post : ", method, body);
    return new Promise((resolve, reject) => {
      this.http.post<any>(this.url + "/" + method, body).subscribe({
        next: data => {
          resolve(data);
          console.log("dataaaaa", data)
        },
        error: error => {
          console.error(method + " Api error");
          resolve(false);
        }
      });
    });
    return true;
  }

  connectToWifi(ssid: string, password: string) {
    this.httpPost('system/connectwifi', {
      "ssid": ssid,
      "pwd": password
    });
  }

  handleWifiClick(wifi: any) {

    if (wifi.security === 'OPEN') {
      // Directly connect without password
      this.connectToWifi(wifi.ssid, '');
    } else {
      this.openWifiPasswordField(wifi.ssid);
    }

  }

  openWifiPasswordField(ssid: any) {

    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: true,
      height: '220px',
      position: {
        top: "10px"
      },
      data: {
        module: 'wifi',
        wifiName: ssid
      },

    };

    const dialog = this.dialog.open(AuthComponent, config);
    dialog.afterClosed().subscribe((res) => {
      console.log('close', res);
      if (res) {
        this.connectToWifi(ssid, res.password);
      }

    });

  }


  async sendScreenSaverData(data: NgForm) {
    console.log("Entering onClick sendScreenSaverData")
    const obj = { status: Boolean(Number(this.screenSaverFormControl.value)), interval_time: Number(data.value.interval_time) };
    this.screenSaverData.emit(obj);
    await this.httpPost(APIS.SCREEN_SAVER, obj);
    console.log("after api call")
  }

  ngOnDestroy(): void {
    setTimeout(()=>{
      this.systemScreen(2);
    },100);

    if (this.intervalId) {
    clearInterval(this.intervalId);
    }
  }

  // --- BATCH SETTINGS METHODS ---

  async getBatchStatus() {
    try {
      let status: any = await new Promise((resolve) => {
        this.http.get<any>(this.url + "/batch").subscribe({
          next: data => resolve(data),
          error: () => resolve({ batch: 0 })
        });
      });
      this.currentBatchStatus = status || { batch: 0 };
    } catch (e) {
      console.log("Error fetching batch status", e);
    }
  }

  async getPreviousBatches() {
    try {
      let list: any = await new Promise((resolve) => {
        this.http.get<any>(this.url + "/batch/list").subscribe({
          next: data => resolve(data),
          error: () => resolve([])
        });
      });
      this.previousBatchesList = (list || []).reverse(); 
    } catch (e) {
      console.log("Error fetching previous batches", e);
    }
  }

  showCreateBatch() {
    this.batchFormData = {
      // batchid: '',
      plantType: this.plantTypes[0],
      startDate: '',
      noOfSlotsPlanted: ''
    };
    this.uiBatchMode = 'create';
  }

  async showEditBatch() {
    this.batchFormData = {
      plantType: this.plantTypes[0],
      day: this.days[0],
      month: this.months[0],
      year: this.years[0],
      noOfSlotsPlanted: ''
    };
    this.uiBatchMode = 'edit';
    
    if (this.currentBatchStatus && this.currentBatchStatus.batchid) {
      try {
        let details: any = await new Promise((resolve) => {
          this.http.get<any>(this.url + "/batch/" + this.currentBatchStatus.batchid + "/details").subscribe({
            next: data => resolve(data),
            error: () => resolve(null)
          });
        });
        if (details) {
          this.batchFormData = { ...this.batchFormData, ...details };
        }
      } catch(e) { }
    }
  }

  showEndBatch() {
    this.batchFormData = {
      slotsHarvested: '',
      weightPerPlant: ''
    };
    this.uiBatchMode = 'end';
  }

  backToBatchDefault() {
    this.uiBatchMode = 'default';
  }

  async createBatch() {
    if (!this.batchFormData.batchid) {
      // Just a check to prevent empty submit
      return;
    }
    await this.httpPost("batch/" + this.batchFormData.batchid + "/create", this.batchFormData);
    await this.getBatchStatus();
    this.backToBatchDefault();
  }

  async saveEditBatch() {
    if (this.currentBatchStatus && this.currentBatchStatus.batchid) {
      const dataToPost = {
        ...this.batchFormData,
        startDate: `${this.batchFormData.day} ${this.batchFormData.month} ${this.batchFormData.year}`
      };
      await this.httpPost("batch/" + this.currentBatchStatus.batchid + "/edit", dataToPost);
      await this.getBatchStatus();
      this.backToBatchDefault();
    }
  }

  async endBatch() {
    if (this.currentBatchStatus && this.currentBatchStatus.batchid) {
      await this.httpPost("batch/" + this.currentBatchStatus.batchid + "/end", this.batchFormData);
      await this.getBatchStatus();
      await this.getPreviousBatches();
      this.backToBatchDefault();
    }
  }
}