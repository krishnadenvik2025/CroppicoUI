import {Options} from '@angular-slider/ngx-slider';
import {Component,ComponentFactoryResolver,OnChanges,OnInit,} from '@angular/core';
import {Apex} from './chartinfo';
import {HttpClient} from '@angular/common/http';
import {environment} from 'src/environments/environment';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { APIS } from 'src/shared/model/api.model';
import { AuthComponent } from 'src/shared/component/auth/auth.component';
import { FlushDialogComponent } from 'src/shared/component/flush-dialog/flush-dialog.component';
import { ChartsComponent } from 'src/shared/component/charts/charts.component';
import { GuideComponent } from 'src/shared/component/guide/guide.component';
import { fromEvent } from 'rxjs';
import { TopupDialogComponent } from 'src/shared/component/topup-dialog/topup-dialog.component';
import { ScreenSaverService } from 'src/core/screen-saver.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit, OnChanges {
  apexChart: any = new Apex();
  url = environment.api;
  wifiUrl = environment.wifi;
  wifi_signal_image: string = '';
  screen_saver_img: string = '';
  title = 'cropicco-ui';
  isShowResetAlarm = false;
  time = new Date();
  show_brightness_slider: boolean = false;
  show_settings_screen: boolean = false;
  show_maintenance_screen: boolean = false;
  show_home_screen: boolean = true;
  show_sensors_screen: boolean = false;
  show_info_screen: boolean = false;
  prevent_toggle: boolean = false;
  allData: any;
  envData: any = {
    total_harvest: 0,
    plastic_waste: 0,
    water_saved: 0,
    food_miles: 0
  };
  currentFooterIndex: number = 0;
  footerInterval: any;
  footerVisible = true;
  footerMessages: any = {
    1: [
      "Homie's 72 plants are actively absorbing CO₂ and releasing fresh oxygen.",
      "Your indoor garden is improving air quality every day.",
      "Plants naturally help regulate humidity levels.",
      "Green spaces contribute to a healthier workspace.",
      "Indoor plants can help reduce stress and improve wellbeing."
    ],
    2: [
      "Aligning your workspace with UN Sustainable Development Goals 2, 12, and 13.",
      "Supporting sustainable consumption and production practices.",
      "Reducing environmental impact through smart monitoring.",
      "Creating awareness about indoor environmental quality.",
      "Building healthier and greener workplaces."
    ]};
  brightness_level: number = 5;
  light_last_updated: number = 0;
  disable_brightness_slider: boolean = false;
  currentMainScreen: number = 0;
  slider_options: Options = {
    floor: 0,
    ceil: 100,
    step: 10,
    vertical: true,
    showTicks: false,
    hidePointerLabels: true,
    hideLimitLabels: true,
    disabled: false
  };
  meterData: any = {
    'water': [0, 0, 0],
    'ambient': [0, 0]
  };
  waterDataStr: String = '';
  ambientDataStr: String = '';
  light_state: any = {
    1: false,
    2: false,
    3: false,
    4: false,
    5: false,
  };
  public isDisabled = false;
  public showScreenSaver = false;
  isIdle = false;
  private idleAfterSeconds = 1000 * 60 * 1;
  private countDown: any;
  public screenSaverStatus: boolean = true;
  mouseMoveSubscription: any;
  touchStartSubscription: any;
  keyDownSubscription: any;
  clickSubscription: any;

  image_urls: any = ["/assets/images/screen_saver/screen_saver_1.jpg", "/assets/images/screen_saver/screen_saver_2.jpg", "/assets/images/screen_saver/screen_saver_3.jpg"];
  clearScreenSaverInterval: any;
  constructor(
    private http: HttpClient,
    private dialog: MatDialog,
    private screensaver: ScreenSaverService) {
    this.screen_saver_img = this.image_urls[0];
  }

  ngOnInit() {
    this.screensaver.screenSaver.subscribe((res: any) => {
      console.log(res);
      this.screenSaverStatus = res;
    })
    this.getSettings();
    this.startFooterRotation();
    this.getData();
    this.getEnvData();
    setInterval(() => {
      this.time = new Date();
      // this.light_1_state = !this.light_1_state;
    }, 1000);
    setInterval(() => {
      if (!this.show_settings_screen && !this.show_maintenance_screen) {
        this.getData();
        this.getEnvData();
      }
    }, 5000);
  }

  fetchImageUrl() {
    let i = 0;
    this.screen_saver_img = this.image_urls[i];
    this.clearScreenSaverInterval = setInterval(() => {
      i++;
      console.log("I", i);

      if ((this.image_urls.length) == i) {
        i = 0;
      }
      this.screen_saver_img = this.image_urls[i];
    }, 1000 * 5);
  }

  ngOnChanges(changes: any) {
    console.log(changes);
  }
  reserAlarm() {
    const obj = {
      retAlarm: true
    };
    this.httpPost(APIS.RESET_ALARM, obj);


  }
  async update() {
    const obj = {
      update: true
    };

    const url = this.wifiUrl;
    console.log('update url', this.wifiUrl);
    this.http.post(url, obj).subscribe(res => {
      console.log('update res', res);
    });

    setTimeout(() => {
      this.isDisabled = false;
    }, 1000 * 10);
  }

  async getData() {
    let dataApiCallData: any = await new Promise((resolve, reject) => {
      this.http
        .get<any[]>(this.url + "/data").subscribe({
          next: data => {
            resolve(data);
          },
          error: error => {
            console.log(error);
            resolve(false);
          }
        });
    });
    console.log("GET DATA", dataApiCallData);
    if (dataApiCallData) {
      this.allData = dataApiCallData;
      // console.log("Ultrasonic",parsed_data);
      this.setWifiSignalImgFn();
      this.brightness_level = dataApiCallData?.data?.light_brightness || 0;
      this.updateStats(this.allData.data);
    } else {
      console.log("Data Api error");
    }
  }

  async getEnvData() {
    let envApiCallData: any = await new Promise((resolve) => {
      this.http
        .get<any>(this.url + "/env/data").subscribe({
          next: data => {
            console.log("GET ENV DATA", data);
            resolve(data);
          },
          error: error => {
            console.log("Env Data Api error", error);
            resolve(false);
          }
        });
    });

    if (envApiCallData) {
      this.envData = {
        total_harvest: envApiCallData.total_harvest || 0,
        plastic_waste: envApiCallData.plastic_waste || 0,
        water_saved: envApiCallData.water_saved || 0,
        food_miles: envApiCallData.food_miles || 0
      };
    }
  }

  startFooterRotation() {
    this.footerInterval = setInterval(() => {
      this.footerVisible = false;

      setTimeout(() => {

        const messages =
          this.footerMessages[this.currentMainScreen] || [];

        if (messages.length) {
          this.currentFooterIndex =
            (this.currentFooterIndex + 1) % messages.length;
        }
        this.footerVisible = true;

      }, 500);

    }, 10000);
  }

  setWifiSignalImgFn = () => {
    const wifi_urls = [
      {
        key: 'low',
        url: '/assets/images/wifi/wifi_low.svg'
      },
      {
        key: 'medium',
        url: '/assets/images/wifi/wifi_mid.svg'
      },
      {
        key: 'good',
        url: '/assets/images/wifi/wifi_full.svg'
      },
      {
        key: 'notconnected',
        url: '/assets/images/wifi/wifi_not_connected.svg'
      },
    ];
    this.wifi_signal_image = wifi_urls
      .find((k) => k.key.includes(this.allData?.data.wifi_strength?.toLowerCase()))?.url
      || '';
    console.log(this.wifi_signal_image)
  };
  openFlushPopUp() {
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: true,
      minWidth: "200px",
      minHeight: '200px',
      data: {
        title: `Flush Water`,
      },
    };

    this.screensaver.updateScreenSaverStatus(false)
    const dialog = this.dialog.open(FlushDialogComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true)
      console.log(result);
    });


  }

  openTopupPopUp() {
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: true,
      minWidth: "200px",
      minHeight: '200px',
      data: {
        title: `Topup Water`,
      },
    };
    this.screensaver.updateScreenSaverStatus(false)
    const dialog = this.dialog.open(TopupDialogComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true)
      console.log(result);
    });


  }
  async resetUserError() {
    // this.httpPost(APIS.USER_ERROR_RESET, { reset: true });
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: true,
      minWidth: "200px",
      minHeight: '200px',
      data: {
        title: `user_error`,
      },
    };
    this.screensaver.updateScreenSaverStatus(false)

    const dialog = this.dialog.open(FlushDialogComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true)

      console.log(result);
    });
  }

  async showCharts() {
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: true,
      minWidth: "900px",
      minHeight: '100px',
      position: { top: "10px" },
      data: {
        title: `Charts`,
      },
    };
    this.screensaver.updateScreenSaverStatus(false)
    const dialog = this.dialog.open(ChartsComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true)

      console.log(result);
    });
  }

  async showGuide() {
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: true,
      minWidth: "900px",
      height: '360px',
      position: { top: "10px" },
      data: {
        title: `Guide`,
      },
    };
    this.screensaver.updateScreenSaverStatus(false)
    const dialog = this.dialog.open(GuideComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true)
      console.log(result);
    });
  }

  // updateStats(data: any) {
  //   if (Object.keys(data).length) {
  //     this.brightness_level = data.light_brightness || 0;
  //     this.meterData = {
  //       'water': [data["water_level"], data["water_flow"], data["water_temperature"]],
  //       'ambient': [data["ambient_humid"], data["ambient_temp"]]
  //     }
  //     // console.log('date ',this.light_last_updated + 60, Math.floor(Date.now() / 1000),this.light_last_updated + 60 < Math.floor(Date.now() / 1000));
  //     // && this.light_last_updated + 60 < Math.floor(Date.now() / 1000)
  //     if (data?.light_stat?.length && this.light_last_updated + 60 < Math.floor(Date.now() / 1000)) {
  //       for (let lS in data?.light_stat) {
  //         this.light_state[parseInt(lS) + 1] = Boolean(data?.light_stat[lS]);
  //       }
  //       this.light_last_updated = Math.floor(Date.now() / 1000);
  //     }

  //   }

  // }

  updateStats(data: any) {
    this.meterData = {
      'water': [data["water_level"], data["water_flow"], data["water_temperature"]],
      'ambient': [data["ambient_humid"], data["ambient_temp"]]
    };
    if (this.light_last_updated + 60 < Math.floor(Date.now() / 1000)) {
      for (let lS in data["light_stat"]) {
        this.light_state[parseInt(lS) + 1] = Boolean(data["light_stat"][lS])
      }
      this.light_last_updated = Math.floor(Date.now() / 1000);
    }
  }

  showInfo() {
    this.show_info_screen = !this.show_info_screen;
    this.show_settings_screen = false;
    this.show_maintenance_screen = false;
    this.show_sensors_screen = false;
    if (!this.show_info_screen) {
      this.show_home_screen = true;
    }
  }

  toggleBrightnessMenu() {
    this.show_brightness_slider = !this.show_brightness_slider;
  }
  openSettings() {
    if (!this.show_settings_screen) {
      const config: MatDialogConfig = {
        panelClass: "dialog-responsive",
        disableClose: true,
        height: '200px',
        data: {
          module: 'settings',
        },
      };
 
      const dialog = this.dialog.open(AuthComponent, config);
      dialog.afterClosed().subscribe((result) => {
        console.log('close', result);
        if (result?.isValid) {
          this.show_settings_screen = !this.show_settings_screen;
          if (this.timerInterval) {
            clearInterval(this.timerInterval);
          }
          this.startCountdown(15)
          this.show_maintenance_screen = false;
          this.show_home_screen = false;
          this.show_info_screen = false;
          this.isShowResetAlarm = false;
        }
      });
    } else {
      this.show_settings_screen = !this.show_settings_screen;
      this.show_maintenance_screen = false;
      this.show_info_screen = false;
      this.show_sensors_screen = false;
      this.isShowResetAlarm = false;
    }
  }
  openMaintenance() {
    if (!this.show_maintenance_screen) {
      const config: MatDialogConfig = {
        panelClass: "dialog-responsive",
        disableClose: true,
        height: '200px',
        data: {
          module: 'maintenance',
        },
      };

      const dialog = this.dialog.open(AuthComponent, config);
      dialog.afterClosed().subscribe((result) => {
        console.log('close', result);
        if (result?.isValid) {
          this.show_maintenance_screen = !this.show_maintenance_screen;
          if (this.timerInterval) {
            clearInterval(this.timerInterval);
          }
          this.startCountdown(20)
          this.show_settings_screen = false;
          this.show_home_screen = false;
          this.show_info_screen = false;
          this.show_sensors_screen = false;
          this.isShowResetAlarm = false;
        }
      });
    }
    else {
      this.show_maintenance_screen = !this.show_maintenance_screen;
      this.show_settings_screen = false;
      this.show_info_screen = false;
      this.show_sensors_screen = false;
      this.isShowResetAlarm = false;
    }
  }
  showHome() {
    console.log("Moving to Home screen");
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }
    this.show_maintenance_screen = false;
    this.show_settings_screen = false;
    this.show_sensors_screen = false;
    this.show_home_screen = true;
  }

  showSensors() {
    this.show_sensors_screen = true;
    this.show_home_screen = false;
    this.show_settings_screen = false;
    this.show_maintenance_screen = false;
    this.show_info_screen = false;
  }
  async onLightBtnChange(lightNum: any) {
    this.prevent_toggle = true;
    setTimeout(() => {
      this.prevent_toggle = false;
    }
      , 1000)
    console.log("onChange EVent")
    console.log(lightNum, this.light_state);
    let bod = {
      light: lightNum,
      state: this.light_state[lightNum] ? 0 : 1
    };
    console.log(bod);
    await this.httpPost("lights", bod);
    this.light_last_updated = Math.floor(Date.now());
  }

  async onLightBrightnessChange() {
    this.disable_brightness_slider = true;
    this.updateSliderOptions();
    setTimeout(() => {
      this.disable_brightness_slider = false;
      this.updateSliderOptions();
    }, 1000)
    console.log(this.brightness_level);
    await this.httpPost("lights", {
      light: 0,
      state: this.brightness_level
    });
  }

  // Method to update slider options dynamically
  updateSliderOptions() {
    this.slider_options = {
      ...this.slider_options,
      disabled: this.disable_brightness_slider
    };
  }

  countdown: string = ''; 
  timerInterval: any; 

  startCountdown(minutes: number) {
    // Convert minutes to milliseconds
    let remainingTime = minutes * 60 * 1000;



    // Initialize the countdown display
    this.updateCountdownDisplay(remainingTime);

    // Start the interval to update the countdown every second
    this.timerInterval = setInterval(() => {
      remainingTime -= 1000; // Decrement the remaining time by 1 second (1000 milliseconds)

      // Update the countdown display
      this.updateCountdownDisplay(remainingTime);

      // Stop the countdown when time runs out
      if (remainingTime <= 0) {
        clearInterval(this.timerInterval);
        if (this.show_maintenance_screen) {
          this.show_maintenance_screen = false
        }
        else if (this.show_settings_screen) {
          this.show_settings_screen = false
        }
        else if (this.show_sensors_screen) {
          this.show_sensors_screen = false
        }
        this.countdown = '00:00'; // Display 00:00 when countdown ends
      }
    }, 1000);
  }

  updateCountdownDisplay(remainingTime: number) {
    // Calculate the remaining minutes and seconds
    const minutes = Math.floor(remainingTime / (1000 * 60));
    const seconds = Math.floor((remainingTime % (1000 * 60)) / 1000);

    // Format minutes and seconds to display as two digits
    const minutesDisplay = minutes.toString().padStart(2, '0');
    const secondsDisplay = seconds.toString().padStart(2, '0');

    // Update the countdown variable with formatted time
    this.countdown = `${minutesDisplay}:${secondsDisplay}`;
    console.log("this.countdown", this.countdown)
  }

  httpPost(method: string, body: any) {
    return new Promise((resolve, reject) => {
      this.http.post<any>(this.url + "/" + method, body).subscribe({
        next: data => {
          resolve(data);
        },
        error: error => {
          console.error(method + " Api error" + JSON.stringify(error));
          resolve(false);
        }
      });
    });
  }
  get currentFooterText(): string {
    return (
      this.footerMessages[this.currentMainScreen]?.[
        this.currentFooterIndex
      ] || ''
    );
  }

  onInteraction(i: any) {
    if (this.isIdle) {
      this.isIdle = false;
      this.showScreenSaver = false;
      console.log('im awake!');
      clearInterval(this.clearScreenSaverInterval);
    }

    clearTimeout(this.countDown);
    this.countDown = setTimeout(() => {
      this.isIdle = true;
      this.showScreenSaver = true && this.screenSaverStatus;
      console.log("this.showScreenSaver", this.showScreenSaver)
      console.log("screenSaverStatus", this.screenSaverStatus)
      console.log('im idle');
      this.fetchImageUrl();
    }, this.idleAfterSeconds);
  }

  screenSaverData(data: any) {
    console.log("screenSaverData", data)
    if (data.status == true) {
      console.log("Entering start loop")
      this.idleAfterSeconds = Number(data.interval_time) * 60 * 1000;
      this.screenSaverFn(1);
    }
    if (data.status !== true) {
      console.log("Entering stop loop")
      this.screenSaverUnSubscribeFn();
    }

  }

  screenSaverFn(i: any) {
    console.log("screeeennnn----->", i)
    this.screenSaverStatus = true;
    this.onInteraction(1);
    this.mouseMoveSubscription = fromEvent(document, 'mousemove').subscribe(() => this.onInteraction(2));
    this.touchStartSubscription = fromEvent(document, 'touchstart').subscribe(() => this.onInteraction(3));
    this.keyDownSubscription = fromEvent(document, 'keydown').subscribe(() => this.onInteraction(4));
    this.clickSubscription = fromEvent(document, 'click').subscribe(() => this.onInteraction(5));

    clearInterval(this.clearScreenSaverInterval);

  }

  screenSaverUnSubscribeFn() {
    console.log("Entering unsubscribe loop")
    this.mouseMoveSubscription?.unsubscribe();
    this.touchStartSubscription?.unsubscribe();
    this.keyDownSubscription?.unsubscribe();
    this.clickSubscription?.unsubscribe();
    this.screenSaverStatus = false;
    // this.onInteraction(10);
    // clearInterval(this.clearScreenSaverInterval);
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
    const data: any = settingApiCallData['system_setting'];
    console.log("screen--->>>>>>", data)

    if (Boolean(Number(data.screensaver_status))) {
      console.log("data.screensaver_status", data.screensaver_status)
      this.idleAfterSeconds = Number(data.screensaver_time) * 60 * 1000;
      console.log("Entering last loop")
      this.screenSaverFn(2);
    }
    else {
      console.log("Entering last else loop")

      this.screenSaverUnSubscribeFn();
    }

  }
}
