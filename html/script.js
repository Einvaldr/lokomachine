function init() {
  var url = window.location.href;
  var params = url.split(/[\&\?=]/);
  var date = decodeURI(params[2]);
  var score = params[4];
  var discount = params[6];
  var time = date.split(/[: -\.]/);
  var finish = new Date(time[0], (time[1] - 1), time[2], time[3], time[4], time[5], 0);
  var update_timer = function() {
    var difference = Math.round((finish - (new Date())) / 1000);
    var minutes = Math.floor(difference / 60);
    if (minutes < 0) {
      minutes = 0;
    }
    var seconds = difference % 60;
    if (seconds < 0) {
      seconds = 0;
    }
    document.getElementById('timer').innerHTML = minutes + ':' + seconds;
  }
  window.setInterval(update_timer, 100);
  update_timer();
  document.getElementById('score').innerHTML = score;
  document.getElementById('discount').innerHTML = discount + '%';
}
