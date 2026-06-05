import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { FormControl, NgForm, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { KeypadComponent } from 'src/app/keypad/keypad.component';

@Component({
  selector: 'app-auth',
  templateUrl: './auth.component.html',
  styleUrls: ['./auth.component.css']
})
export class AuthComponent implements OnInit {
  public hide = true;
  public isPassword = false;
  public closeKeyboard = false;
  public password = new FormControl('', [Validators.required]);
  public wifiPassword = new FormControl('', [Validators.required]);
  constructor(public dialogRef: MatDialogRef<AuthComponent>,
    private http: HttpClient,
    private modalService: NgbModal,
    @Inject(MAT_DIALOG_DATA) public dialogData: any,
  ) { }

  ngOnInit(): void {
    console.log('dialogData', this.dialogData);
  }
  isValidPassword() {
    if (this.password.invalid) {
      return
    }
    if (this.dialogData?.module == 'settings') {
      this.password.value == '0806' ? this.dialogRef.close({ isValid: true }) : this.password.setErrors({ 'incorrect': true });

    }
    if (this.dialogData?.module == 'maintenance') {
      this.password.value == '0608' ? this.dialogRef.close({ isValid: true }) : this.password.setErrors({ 'incorrect': true });

    }



  }

  sendPassword() {

    if (this.wifiPassword.invalid) {
      return
    }

    if (this.dialogData?.module == 'wifi') {
      this.dialogRef.close({ password: this.wifiPassword.value });

    }

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
    modalRef.componentInstance.defVal = this.password.value;
    modalRef.componentInstance.passEntry.subscribe((receivedEntry: any) => {
      console.log("Received Data:", receivedEntry, tempFormVal);
      this.password.setValue(receivedEntry);
      modalRef.close();
    });
  }
}
