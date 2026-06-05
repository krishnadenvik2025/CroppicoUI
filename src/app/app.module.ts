import { NgModule } from '@angular/core';
import { BrowserModule, HammerModule } from '@angular/platform-browser';

import { AppComponent } from './app.component';
import { SettingsComponent } from './settings/settings.component';
import { MaintenanceComponent } from './maintenance/maintenance.component';
import { NgCircleProgressModule } from 'ng-circle-progress';
import { UiSwitchModule } from 'ngx-toggle-switch';
import { NgxSliderModule } from '@angular-slider/ngx-slider';
import { NgApexchartsModule } from 'ng-apexcharts';
import { NgbModalModule, NgbModule, NgbCarousel } from '@ng-bootstrap/ng-bootstrap';
import { MainstatusComponent } from './mainstatus/mainstatus.component';
import { NgxVirtualKeyboardModule } from 'ngx-virtual-keyboard';
// import { NgVirtualKeyboardModule } from '@protacon/ng-virtual-keyboard';
import { KeypadComponent } from './keypad/keypad.component';
import { HttpClientModule } from '@angular/common/http';
import { QrCodeModule } from 'ng-qrcode';
import { KeyboardComponent } from './keyboard/keyboard.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MaterialModule } from 'src/assets/material/material.module';
import { SharedModule } from 'src/shared/shared.module';
import { MatKeyboardModule } from 'angular-onscreen-material-keyboard';
import { InfoComponent } from './info/info.component';
import { DisableOneSecDirective } from 'src/shared/directives/disable-one-sec.directive';
import { PdfViewerModule } from 'ng2-pdf-viewer';
import { ScreenSaverService } from 'src/core/screen-saver.service';
import { SensorsComponent } from './sensors/sensors.component';

@NgModule({
  declarations: [
    AppComponent,
    SettingsComponent,
    MaintenanceComponent,
    MainstatusComponent,
    KeypadComponent,
    KeyboardComponent,
    InfoComponent,
    DisableOneSecDirective,
    SensorsComponent
  ],
  imports: [
    BrowserModule,
    HammerModule,
    NgCircleProgressModule.forRoot({
      // set defaults here
      radius: 100,
      outerStrokeWidth: 16,
      innerStrokeWidth: 8,
      outerStrokeColor: "#209100",
      innerStrokeColor: "#C7E596",
      animationDuration: 200
    }),
    UiSwitchModule,
    NgxSliderModule,
    NgApexchartsModule,
    MatKeyboardModule,
    NgbModalModule,
    NgbModule,
    HttpClientModule,
    QrCodeModule,
    BrowserAnimationsModule,
    MaterialModule,
    SharedModule,
    PdfViewerModule


  ],
  providers: [
    KeypadComponent,
    ScreenSaverService
  ],
  entryComponents: [SettingsComponent],
  bootstrap: [AppComponent]
})

export class AppModule { }