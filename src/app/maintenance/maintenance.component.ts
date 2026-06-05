import {
  Component,
  OnDestroy,
  OnInit
} from '@angular/core';
import {
  HttpClient
} from '@angular/common/http';
import {
  NgbModal
} from '@ng-bootstrap/ng-bootstrap';
import {
  environment
} from 'src/environments/environment';
import {
  NgForm
} from '@angular/forms';
import {
  KeypadComponent
} from '../keypad/keypad.component';

@Component({
  selector: 'app-maintenance',
  templateUrl: './maintenance.component.html',
  styleUrls: ['./maintenance.component.css']
})
export class MaintenanceComponent implements OnInit, OnDestroy {
  url = environment.api;
  adhocSet: any = {
    water_pump: 0,
    water_temperature_time: 0,
    ec_pump: 0,
    ph_inc_pump: 0,
    ph_decc_pump: 0,
    light_brightness_time: 0,
    flush_pump : 0,
    topup_pump : 0
  }

  constructor(private modalService: NgbModal,
    private http: HttpClient) { }

  ngOnInit(): void { 
    setTimeout(()=>{
      this.systemScreen(1);
    },100)
  }

  updateAdhocSettings(form: NgForm) {
    let payload = {
      "water_pump": form.value.water_pump.toString() + ":00",
      "water_temperature_time": form.value.water_temperature_time.toString() + ":00",
      "ec_pump": "00:" + form.value.ec_pump,
      "ph_inc_pump": "00:" + form.value.ph_inc_pump,
      "ph_decc_pump": "00:" + form.value.ph_decc_pump,
      "flush_pump": form.value.flush_pump.toString() + ":00",
      "topup_pump": form.value.topup_pump.toString() + ":00"
    }
    console.log(payload)
    this.httpPost('/adhoc/start', payload);
  }

  open(form: NgForm, inputItem: any) {
    console.log("Opening Modal", form.value, inputItem)
    let tempFormVal = form.value;
    const modalRef = this.modalService.open(KeypadComponent, {
      size: 'sm',
      backdrop: 'static',
      centered: true,
      scrollable: false
    });
    console.log('tempFormVal[inputItem]', tempFormVal[inputItem]);
    const value = tempFormVal[inputItem];
    modalRef.componentInstance.defVal = tempFormVal[inputItem]
    modalRef.componentInstance.passEntry.subscribe((receivedEntry: any) => {
      const isValidFn = (obj: any) => {
        if (this.minMaxFn(obj)) {
          tempFormVal[inputItem] = receivedEntry;
          form.setValue(tempFormVal);
        } else {
          tempFormVal[inputItem] = value;
          form.setValue(tempFormVal);
        }
      }
      console.log("Received Data:", receivedEntry, tempFormVal);
      let obj = {};
      switch (true) {
        case inputItem == 'water_pump':
          obj = {
            min: 0,
            max: 5,
            value: Number(receivedEntry)
          }
          isValidFn(obj);
          break;
        case inputItem == 'water_temperature_time':
          obj = {
            min: 0,
            max: 10,
            value: Number(receivedEntry)
          }
          isValidFn(obj);
          break;
        case inputItem == 'ec_pump':
          obj = {
            min: 0,
            max: 60,
            value: Number(receivedEntry)
          }
          isValidFn(obj);
          break;
        case inputItem == 'ph_inc_pump':
          obj = {
            min: 0,
            max: 60,
            value: Number(receivedEntry)
          }
          isValidFn(obj);
          break;
        case inputItem == 'ph_decc_pump':
          obj = {
            min: 0,
            max: 60,
            value: Number(receivedEntry)
          }
          isValidFn(obj);
          break;
          case inputItem == 'flush_pump':
          obj = {
            min: 0,
            max: 5,
            value: Number(receivedEntry)
          }
          isValidFn(obj);
          break;
          case inputItem == 'topup_pump':
          obj = {
            min: 0,
            max: 5,
            value: Number(receivedEntry)
          }
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

  async systemScreen(index:any) {
    let payloadData;
    if(index == 1)
    {
      payloadData = {
        "screen":"maintanence",
        "status":"true"
      }
    }
    if(index == 2)
      {
        payloadData = {
          "screen":"maintanence",
          "status":"false"
        }
      }
    
    this.httpPost("system/screen", payloadData);

  }
  httpPost(method: string, body: any) {
    console.log("Http Post : ", method, body)
    return new Promise((resolve, reject) => {
      this.http.post<any>(this.url + "/" + method, body).subscribe({
        next: data => {
          resolve(data)
        },
        error: error => {
          console.error(method + " Api error");
          resolve(false)
        }
      })
    })
  }

  ngOnDestroy(): void {
    setTimeout(()=>{
      this.systemScreen(2);
    },100);
  }

}