import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'app-info',
  templateUrl: './info.component.html',
  styleUrls: ['./info.component.css']
})
export class InfoComponent implements OnInit {
  @Input() meterData: any;
  @Input() allData: any;
  infoData: any = [];
  sortOrder = ["water_ec", "water_pH", "ec_a_pump", "ec_b_pump", "ph_inc_pump", "ph_dec_pump", "chiller_state",
    "irrigation_state", "water_level", "water_flow", "supp_ec_a", "supp_ec_b", "supp_ph_inc", "supp_ph_dec", "light_stat", "light_brightness",
    "water_temperature", "ambient_temp", "ambient_humid", "error"]


  constructor() {
  }

  ngOnInit(): void {
    this.initFn();
    setInterval(() => {
      this.initFn()
    }, 2000);
  }

  initFn() {
    if (this.allData?.data) {
      const ordered = Object.keys(this.allData?.data).sort((a: any, b: any) => this.sortOrder.indexOf(a) - this.sortOrder.indexOf(b)).reduce(
        (obj: any, key) => {
          obj[key] = this.allData?.data[key];
          return obj;
        },
        {}
      );
      const obj = []
      for (let [key, value] of Object.entries(ordered)) {
        obj.push({
          key: key.replace(/[^a-zA-Z ]/g, " ").toLocaleUpperCase(), value
        })
      }
      this.infoData = [];
      this.infoData = obj;
      console.log("INFODARA",this.infoData)
    }

  }
}
