import { Options } from '@angular-slider/ngx-slider';
import { Component, ComponentFactoryResolver, OnChanges, OnInit, } from '@angular/core';
import { Apex } from './chartinfo';
import { HttpClient } from '@angular/common/http';
import { environment } from 'src/environments/environment';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { APIS } from 'src/shared/model/api.model';
import { AuthComponent } from 'src/shared/component/auth/auth.component';
import { FlushDialogComponent } from 'src/shared/component/flush-dialog/flush-dialog.component';
import { ChartsComponent } from 'src/shared/component/charts/charts.component';
import { GuideComponent } from 'src/shared/component/guide/guide.component';
import { fromEvent } from 'rxjs';
import { TopupDialogComponent } from 'src/shared/component/topup-dialog/topup-dialog.component';
import { WaterControlDialogComponent } from 'src/shared/component/water-control-dialog/water-control-dialog.component';
import { EmResetDialogComponent } from 'src/shared/component/em-reset-dialog/em-reset-dialog.component';
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
  show_info_screen: boolean = false;
  prevent_toggle: boolean = false;
  allData: any;
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
  lightPanelExpanded: boolean = true;
  readonly lightZoneOrder = [1, 2, 3, 4, 5];
  // readonly lightHues: { [key: number]: string } = {
  //   1: '#2E9FC7',
  //   2: '#8A5FD6',
  //   3: '#B08122',
  //   4: '#2E7FD6',
  //   5: '#1E8E56',
  // };
  readonly lightHues: { [key: number]: string } = {
    1: '#2E9FC7',
    2: '#2E9FC7',
    3: '#2E9FC7',
    4: '#2E9FC7',
    5: '#2E9FC7',
  };

  get anyLightOn(): boolean {
    return this.lightZoneOrder.some(i => this.light_state[i]);
  }

  get lightMasterBg(): string {
    if (this.lightPanelExpanded) return '#16241B';
    return this.anyLightOn ? '#F5B94D' : '#EEF1EA';
  }

  get lightMasterStroke(): string {
    if (this.lightPanelExpanded) return '#FFFFFF';
    return this.anyLightOn ? '#FFFFFF' : '#9AA79C';
  }

  get lightMasterGlow(): string {
    if (this.lightPanelExpanded) return '0 2px 8px rgba(0,0,0,0.2)';
    return this.anyLightOn ? '0 0 10px #F5B94D80' : 'none';
  }

  toggleLightPanel() {
    this.lightPanelExpanded = !this.lightPanelExpanded;
  }
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

  image_urls: any = ["/assets/images/screen_saver/screen_saver_1.jpg"];
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
    this.getData();

    setInterval(() => {
      this.time = new Date();
    }, 1000);
    setInterval(() => {
      if (!this.show_settings_screen && !this.show_maintenance_screen) {
        this.getData();
      }
    }, 20000);
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
    }, 1000 * 20);
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

  async EMReset() {
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: false,
      minWidth: "320px",
      data: {
        title: "Energy Meter Reset",
      },
    };
    this.screensaver.updateScreenSaverStatus(false);
    const dialog = this.dialog.open(EmResetDialogComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true);
      console.log('EMReset dialog closed:', result);
      this.isDisabled = false;
    });
  }

  openWaterControlPopUp() {
    const config: MatDialogConfig = {
      panelClass: "dialog-responsive",
      disableClose: false,
      minWidth: "360px",
      data: {
        title: "Water Control",
      },
    };
    this.screensaver.updateScreenSaverStatus(false);
    const dialog = this.dialog.open(WaterControlDialogComponent, config);
    dialog.afterClosed().subscribe((result) => {
      this.screensaver.updateScreenSaverStatus(true);
      console.log('Water control dialog closed:', result);
    });
  }

  async waterControl() {
    this.openWaterControlPopUp();
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
          this.isShowResetAlarm = false;
        }
      });
    }
    else {
      this.show_maintenance_screen = !this.show_maintenance_screen;
      this.show_settings_screen = false;
      this.show_info_screen = false;
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
    this.show_home_screen = true;
  }
  async onLightBtnChange(lightNum: any) {
    this.light_state[lightNum] = !this.light_state[lightNum];
    this.prevent_toggle = true;
    setTimeout(() => { this.prevent_toggle = false; }, 1000)
    console.log("onChange EVent")
    console.log(lightNum, this.light_state);
    let bod = {
      light: lightNum,
      state: this.light_state[lightNum] ? 1 : 0
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

  updateSliderOptions() {
    this.slider_options = {
      ...this.slider_options,
      disabled: this.disable_brightness_slider
    };
  }

  countdown: string = '';
  timerInterval: any;

  startCountdown(minutes: number) {
    let remainingTime = minutes * 60 * 1000;
    this.updateCountdownDisplay(remainingTime);
    this.timerInterval = setInterval(() => {
      remainingTime -= 1000;
      this.updateCountdownDisplay(remainingTime);
      if (remainingTime <= 0) {
        clearInterval(this.timerInterval);
        if (this.show_maintenance_screen) {
          this.show_maintenance_screen = false
        }
        else if (this.show_settings_screen) {
          this.show_settings_screen = false
        }
        this.countdown = '00:00';
      }
    }, 1000);
  }
  updateCountdownDisplay(remainingTime: number) {
    const minutes = Math.floor(remainingTime / (1000 * 60));
    const seconds = Math.floor((remainingTime % (1000 * 60)) / 1000);
    const minutesDisplay = minutes.toString().padStart(2, '0');
    const secondsDisplay = seconds.toString().padStart(2, '0');

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
